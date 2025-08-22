import io
import os
import ssl
import smtplib
import tempfile
from io import BytesIO
from django.conf import settings
from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, \
    Spacer, Image, Table, TableStyle
from reportlab.lib import colors
from .models import Dispatch, DispatchImage, Ticket, Comment
from django.utils.timezone import now
from datetime import timedelta
from django.core.serializers import serialize
from mashauri.documents import DispatchDocument
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib import messages
from django.shortcuts import render
from reportlab.lib.pagesizes import letter, landscape


def rename_uploaded_file(file_obj, building_id, folder, prefix):
    try:
        if not file_obj:
            return None 

        if not hasattr(file_obj, 'read'):
            return None 

        original_extension = os.path.splitext(getattr(file_obj, 'name', ''))[1] or ".bin"
        filename = f"{folder}/{prefix}-{building_id}{original_extension}"

        file_content = file_obj.read()
        file_path = default_storage.save(filename, ContentFile(file_content))
        return file_path

    except Exception as e:
        return None


# Modify the role decorator to redirect to the appropriate dashboard
def role_required(required_role, redirect_url_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not (
                request.user.is_authenticated) or (
                    request.user.role != required_role):
                return redirect(reverse(redirect_url_name))
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# Admin users only
def admin_required(view_func):
    return role_required('ADMIN', 'admin_dashboard')(view_func)


# MSP users only
def msp_required(view_func):
    return role_required('MSP', 'msp_dashboard')(view_func)


# Enterprise Connectivity users only
def enterprise_connectivity_required(view_func):
    return role_required('ENTERPRISE_CONNECTIVITY', 'ec_dashboard')(view_func)


# Enterprise Project users only
def enterprise_project_required(view_func):
    return role_required(
        'ENTERPRISE_PROJECT', 'enterprise_project_dashboard')(view_func)


# Support users only
def support_required(view_func):
    return role_required(
        'SUPPORT', 'support_dashboard')(view_func)


# Rollout Partner users only
def rollout_partner_required(view_func):
    return role_required(
        'ROLLOUT_PARTNER', 'rollout_partner_dashboard')(view_func)


def send_mail(recipients, subject, message, attachment_path=None):
    # try:
    if settings.MAIL_SSL:
        server_type = smtplib.SMTP_SSL
    else:
        server_type = smtplib.SMTP

    msg = MIMEMultipart()
    msg['From'] = settings.EMAIL_HOST_USER
    msg['To'] = ', '.join(
        recipients) if isinstance(
            recipients, list) else recipients
    msg['Subject'] = subject

    msg.attach(MIMEText(message, 'plain'))

    # If an attachment is provided, add it
    if attachment_path:
        for attachment_p in attachment_path:
            if isinstance(attachment_p, ContentFile):
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment_p.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={attachment_p.name}.pdf",
                )
                msg.attach(part)
            elif os.path.isfile(attachment_p):  # Check if it's a file
                with open(attachment_p, "rb") as attachment:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={attachment_p.split('/')[-1]}",
                )
                msg.attach(part)
            else:
                pass

    # Connect to the email server and send the message
    with server_type(
        settings.MAIL_HOST_SERVER,
        settings.EMAIL_HOST_PORT,
            context=ssl.create_default_context()) as server:
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
        server.sendmail(settings.EMAIL_HOST_USER, recipients, msg.as_string())

    print(f"Email successfully sent to {recipients}")


def generate_pdf(
        site_fdt_cluster_link_name,
        lepton_project_name,
        msp,
        project_type,
        comments,
        site_fdt_location,
        interception_location,
        tid):

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.black,
        spaceAfter=20,
        alignment=1,  # Centered
    )

    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.black,
        spaceAfter=15,
    )

    normal_style = ParagraphStyle(
        'Body',
        parent=styles['BodyText'],
        fontSize=11,
        textColor=colors.black,
        spaceAfter=12,
    )

    # Use local logo (like your original)
    logo_path = os.path.join(settings.MEDIA_ROOT, 'logos', 'logo.png')  # Customize as needed
    logo = Image(logo_path, width=561/4, height=445/4)

    elements = [
        logo,
        Spacer(1, 12),
        Paragraph("Optimized Escalation/Dispatch Ticket", title_style),
        Paragraph(f"Ticket ID: MSH-{str(tid).zfill(6)}", header_style),
        Spacer(1, 12),
    ]

    # Data table (simplified args but styled like your favorite version)
    data = [
        ['PROPERTY', 'VALUE'],
        ['Site/FDT Cluster Link Name', site_fdt_cluster_link_name],
        ['Lepton Project Name', lepton_project_name],
        ['Site FDT Location', site_fdt_location],
        ['MSP', msp],
        ['Project Type', project_type],
        ['Interception Location', interception_location],
    ]

    table = Table(data, colWidths=[doc.width / 2.0] * 2)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.black),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))

    elements.append(table)
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"Comments: {comments}", normal_style))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        f"Electronically generated by Mashauri System - Ticket #{str(tid).zfill(6)}",
        styles['Italic']
    ))

    doc.build(elements)
    buf.seek(0)
    return buf, str(tid).zfill(6)


def calculate_time_fields(dispatch):
    """
    Calculate time-related fields for a dispatch.
    """
    time_remaining = dispatch.sla_timer - now()
    dispatch.time_remaining = time_remaining

    if dispatch.status == 'Closed':
        time_since_closed = now() - dispatch.sla_timer
        if time_since_closed > timedelta(0):
            days = time_since_closed.days
            hours = time_since_closed.seconds // 3600
            minutes = (time_since_closed.seconds % 3600) // 60
            dispatch.closed_time_display = (
                f"Closed {days} days {hours} hours {minutes} minutes ago")
        else:
            dispatch.closed_time_display = "Closed just now"
    else:
        dispatch.closed_time_display = None

    if time_remaining < timedelta(0):
        time_after_expiration = abs(time_remaining)
        days = time_after_expiration.days
        hours = time_after_expiration.seconds // 3600
        minutes = (time_after_expiration.seconds % 3600) // 60
        dispatch.time_remaining_display = (
            f"Expired {days} days {hours} hours {minutes} minutes ago")
    else:
        days = time_remaining.days
        hours = time_remaining.seconds // 3600
        minutes = (time_remaining.seconds % 3600) // 60
        dispatch.time_remaining_display = (
            f"{days} days {hours} hours {minutes} minutes")

    return dispatch


def calculate_status_counts(dispatches):
    """
    Calculate status counts for dispatches.
    """
    status_counts = {'Hold': 0, 'Progress': 0, 'Closed': 0, 'breached': 0}

    for dispatch in dispatches:
        if dispatch.time_remaining < timedelta(0):
            status_counts['breached'] += 1
        status_counts[dispatch.status] += 1

    return status_counts


def get_filtered_dispatches(category_field, category_value, status=None):
    """
    Filter dispatches based on user category and status.
    """
    if not category_field and not category_value:
        if status == 'Closed':
            return Dispatch.objects.filter(
                status='Closed').order_by('-closed_at')
        elif status == 'Progress':
            return Dispatch.objects.filter(status='Progress')
        elif status == 'Hold':
            return Dispatch.objects.filter(status='Hold')
        else:
            return Dispatch.objects.all()
    filters = {category_field: category_value}
    if status:
        filters['status'] = status
    return Dispatch.objects.filter(**filters).order_by('-sla_timer')


def get_search_results(q, fields):
    """
    Perform search if a query is provided.
    """
    if q:
        search_query = DispatchDocument.search().query(
            "multi_match", query=q, fields=fields
        )
        dispatch_ids = [dispatch.id for dispatch in search_query.to_queryset()]
        return Dispatch.objects.filter(id__in=dispatch_ids), True
    return None, False


def build_context(user, category_field, category_value, request):
    """
    Build a context dictionary for the dashboard views.
    """
    all_dispatches = get_filtered_dispatches(category_field, category_value)
    closed_dispatches = get_filtered_dispatches(
        category_field, category_value, 'Closed')
    closed_dispatches_count = closed_dispatches.count()
    closed_dispatches_json = serialize('json', closed_dispatches)

    active_dispatches = get_filtered_dispatches(
        category_field, category_value, 'Progress').count()
    expired_dispatches = all_dispatches.filter(
        sla_timer__lte=now(), status='Progress').count()

    q = request.GET.get("q")
    search_dispatches, searched = get_search_results(
        q, ["msp", "site_fdt_cluster_link_name", "lepton_project_name", "project_type"])
    if search_dispatches:
        all_dispatches = search_dispatches

    # Calculate time fields and status counts
    all_dispatches = [
        calculate_time_fields(dispatch) for dispatch in all_dispatches]

    def get_closure_message(expired_at, closed_at):
        if not expired_at or not closed_at:
            return "Not enough data to determine closure time."
        
        duration = abs(closed_at - expired_at)
        days = duration.days
        hours, remainder = divmod(duration.seconds, 3600)
        minutes = remainder // 60

        return f"Closed after {days} days, {hours} hours, and {minutes} minutes expiration."
    
    for dispatch in all_dispatches:
        dispatch.closure_message = get_closure_message(dispatch.expired_at, dispatch.closed_at)
    
    status_counts_user = calculate_status_counts(all_dispatches)
    status_counts_all = calculate_status_counts(all_dispatches)

    data = {
        'user': user,
        'status_counts': status_counts_user,
        'status_counts_all': status_counts_all,
        'dispatches': all_dispatches,
        'active_dispatches': active_dispatches,
        'total_dispatches_all': sum(status_counts_user.values()),
        'breached': expired_dispatches,
        'closed_dispatches_json': closed_dispatches_json,
        'closed_dispatches_count': closed_dispatches_count,
        'MEDIA_URL': settings.MEDIA_URL,
        'searched': searched
    }
    return data


def extract_dispatch_data(request):
    """Extract relevant data from the request."""
    return {
        'site_fdt_cluster_link_name': request.POST.get('site_fdt_cluster_link_name'),
        'lepton_project_name': request.POST.get('lepton_project_name'),
        'site_fdt_location': request.POST.get('site_fdt_location'),
        'msp': request.POST.get('msp'),
        'rp': request.POST.get('rp'),
        'project_type': request.POST.get('project_type'),
        'interception_location': request.POST.get('interception_location'),
        'comments': request.POST.get('comments'),
        'fdd_image': request.FILES.get('fdd_image'),
        'hld_image': request.FILES.get('hld_image')
    }


def save_dispatch(data, user):
    """Save the Dispatch instance."""
    dispatch = Dispatch(
        site_fdt_cluster_link_name=data['site_fdt_cluster_link_name'],
        lepton_project_name=data['lepton_project_name'],
        msp=data['msp'],
        rp=data['rp'],
        project_type=data['project_type'],
        comments=data['comments'],
        site_fdt_location=data['site_fdt_location'],
        interception_location=data['interception_location'],
        user=user,
    )
    hld_image = rename_uploaded_file(data['hld_image'], data['site_fdt_cluster_link_name'], 'hld_images', 'HLD-Image')
    fdd_image = rename_uploaded_file(data['fdd_image'], data['site_fdt_cluster_link_name'], 'fdd_images', 'FDD-Image')
    dispatch.hld_image = hld_image
    dispatch.fdd_image = fdd_image
    dispatch.save()
    return dispatch


def save_dispatch_image(dispatch, dispatch_image):
    """Save dispatch image to the database."""
    file_path = default_storage.save(
        dispatch_image.name, ContentFile(dispatch_image.read()))
    DispatchImage.objects.create(
        dispatch=dispatch,
        image=file_path,
        image_type='creation'
    )


def create_ticket_and_pdf(dispatch, data):
    """Create a ticket and its associated PDF."""
    ticket = Ticket.objects.create(dispatching=dispatch, status='Open')
    pdf_buffer, pdf_id = generate_pdf(
        data['site_fdt_cluster_link_name'], data['lepton_project_name'], data['msp'],
        data['project_type'], data['comments'], data['site_fdt_location'],
        data['interception_location'], ticket.id
    )
    filename = f"{pdf_id}.pdf"

    _ = default_storage.save(filename, ContentFile(pdf_buffer.getvalue()))
    ticket.name = filename
    ticket.save()
    return pdf_buffer, ticket


def build_escalation_url(request, dispatch_id):
    """Construct the escalation URL."""
    escalation_url = reverse('dispatch_detail', kwargs={'pk': dispatch_id})
    return request.build_absolute_uri(escalation_url)


def determine_email_recipients(msp, rp):
    """Determine the email recipients based on MSP, and user role."""
    msp_emails = {
        'Egypro': [
            "fnmc@egypro.com", "Fnmc_provisioning@egypro.com", "vmulongo@safaricom.co.ke", "mmutemi@safaricom.co.ke", "nirungu@safaricom.co.ke", "ckimani2@safaricom.co.ke", "condiere@safaricom.co.ke", "FixedNetworkSolutionsPlanning@Safaricom.co.ke", "HomeImplementation@Safaricom.co.ke", "HomeFixedWirelessAccess@Safaricom.co.ke", "FixedCapacityOptimization@Safaricom.co.ke", "sogola@safaricom.co.ke"],
        'Camusat': [
            "noc.kenya@camusat.com",
            "wmureithi@camusat.com", "kogutu@camusat.com", "jkomba@camusat.com", "vmulongo@safaricom.co.ke", "mmutemi@safaricom.co.ke", "nirungu@safaricom.co.ke", "ckimani2@safaricom.co.ke", "condiere@safaricom.co.ke", "FixedNetworkSolutionsPlanning@Safaricom.co.ke", "HomeImplementation@Safaricom.co.ke", "HomeFixedWirelessAccess@Safaricom.co.ke", "FixedCapacityOptimization@Safaricom.co.ke", "sogola@safaricom.co.ke"],
        'Adrian': [
            "nmc-fiber@adriankenya.com", "coreprovisioning@adriankenya.com", "cedrick.kamitu@adriankenya.com", "vmulongo@safaricom.co.ke", "mmutemi@safaricom.co.ke", "nirungu@safaricom.co.ke", "ckimani2@safaricom.co.ke", "condiere@safaricom.co.ke", "FixedNetworkSolutionsPlanning@Safaricom.co.ke", "HomeImplementation@Safaricom.co.ke", "HomeFixedWirelessAccess@Safaricom.co.ke", "FixedCapacityOptimization@Safaricom.co.ke", "sogola@safaricom.co.ke"],
        'Kinde': [
            "noc@kinde.co.ke",
            "james.amboso@kinde.co.ke", "mpengu@kinde.co.ke", "vmulongo@safaricom.co.ke", "mmutemi@safaricom.co.ke", "nirungu@safaricom.co.ke", "ckimani2@safaricom.co.ke", "condiere@safaricom.co.ke", "FixedNetworkSolutionsPlanning@Safaricom.co.ke", "HomeImplementation@Safaricom.co.ke", "HomeFixedWirelessAccess@Safaricom.co.ke", "FixedCapacityOptimization@Safaricom.co.ke", "sogola@safaricom.co.ke"],
        'Fireside': [
            "noc@fireside.africa",
            "hosea@fireside.africa", "vmulongo@safaricom.co.ke", "mmutemi@safaricom.co.ke", "nirungu@safaricom.co.ke", "ckimani2@safaricom.co.ke", "condiere@safaricom.co.ke", "FixedNetworkSolutionsPlanning@Safaricom.co.ke", "HomeImplementation@Safaricom.co.ke", "HomeFixedWirelessAccess@Safaricom.co.ke", "FixedCapacityOptimization@Safaricom.co.ke", "sogola@safaricom.co.ke"],
        'Soliton': [
            "noc@soliton.co.ke",
            "vincent.omondi@soliton.co.ke",
            "vmulongo@safaricom.co.ke", "mmutemi@safaricom.co.ke", "nirungu@safaricom.co.ke", "ckimani2@safaricom.co.ke", "condiere@safaricom.co.ke", "FixedNetworkSolutionsPlanning@Safaricom.co.ke", "HomeImplementation@Safaricom.co.ke", "HomeFixedWirelessAccess@Safaricom.co.ke", "FixedCapacityOptimization@Safaricom.co.ke", "sogola@safaricom.co.ke"]
    }

    rp_emails = {
        'Powergen': ["pmwangi@powergentechnologies.co.ke", "ochieng@powergentechnologies.co.ke", "kinywa@powergentechnologies.co.ke", "gonyango@powergentechnoogies.co.ke"],
        'Hatikvah': ["joseph.chege@hatkivah.co.ke"],
        'Fireside': ["rofas@fireside.africa", "beatrice@fireside.africa", "jane@fireside.africa", "linah@fireside.africa", "benard@fireside.co.ke"],
        'Kinde': ["philip@kinde.co.ke", "faith@kinde.co.ke", "mary.muriithi@kinde.co.ke", "lidigu@kinde.co.ke"],
        'Camusat': ["dmuema@camusat.com"],
        'Techminds': ["nkarambu@techminds.co.ke", "alexkarani@techminds.co.ke", "mmusyoka@techminds.co.ke"],
        'Egypro': ["Josephine_Kathure@egypro.com", "yashi_ndeje@egypro.com", "diana_okware@egypro.com"],
        'Optimax': ["tracy.kigen@otimaxgroup.co.ke"],
        'Pavicon': ["philip.omoiti@pavicon.co.ke", "kangogo@pavicon.co.ke", "josephine.lundi@pavicon.co.ke"],
        'Adrian': ["Winnie.kamweti@adriankenya.com", "edna.kimani@adriankenya.com", "joseph.kimani@adriankenya.com"],
        'Tetranet': ["francis@tetranet.co.ke"],
        'Acl': ["jane@aclkenya.co.ke", "lmburu@aclkenya.co.ke", "joyce@aclkenya.co.ke", "amos@aclkenya.co.ke"],
        'Quavatel': ["florence.njoki@quavatel.com", "peter.kuria@quavatel.com", "hudson.ngaria@quavatel.com"],
        'Extra Dimensions': ["eric.chiero@extra-dimensions.com", "amos.mutethia@extra-dimensions.com"],
        'Decko': ["moses@construction.co.ke", "anthony@construction.co.ke", "david@construction.co.ke"],
        'Soliton': ["francis.ouma@soliton.co.ke", "musa.abikar@soliton.co.ke", "mkioko@soliton.co.ke", "noc@soliton.co.ke"],
        'Blockchain': ["waliaula@blockchainafrica.co.ke"],
        'Huawei': ["james.maina.michoro@huawei.com", "amos.muriuki@huawei.com", "titus.mwendwa.kyalo1@h-partners.com"],
        'Nextgen': ["theo@nextgenke.com"],
        'Geonet': ["gilbert.kibet@geonet-tech.co.ke"],
    }

    recipients = msp_emails.get(msp, [])
    if rp in rp_emails:
        recipients += rp_emails[rp]
    return recipients


def send_notification_email(
        project_type, recipients,
        site_fdt_cluster_link_name, interception_location,
        msp, rp, full_url, attachment_path):
    subject = None
    message = None

    """Send an email notification."""
    subject = (
        f"Core Provisioning Request \"{ site_fdt_cluster_link_name }\" Located at "
        f"\"{interception_location}\"."
    )
    message = (
        f"Please note that \"{site_fdt_cluster_link_name}\" Located at \"{ interception_location }\" "
        f"has been escalated to \"{msp}\" for core provisioning.\n\n"
        f"Click here for details: {full_url}.\n\nMashauri | Core."
    )
    print(subject, message, recipients)
    # send_mail(recipients, subject, message, attachment_path)


def prepare_email_details(dispatch, comment_content, full_url, action):
    """Prepare the email subject and message based on the action type."""
    if action == "update":
        subject = (
            f"Core Provisioning Updates \"{dispatch.site_fdt_cluster_link_name}\" "
            f"Located at \"{dispatch.interception_location}\"."
        )
        message = (
            f"Please note that Core Provisioning Request for "
            f"\"{dispatch.site_fdt_cluster_link_name}\" located at "
            f"\"{dispatch.interception_location}\" "
            f"has been updated with the following comments:\n\n"
            f"\"{comment_content}\".\n\n"
            f"Click here for details: {full_url}.\n\nMashauri | Core."
        )
    elif action == "close":
        subject = (
            f"Core Provisioning for \"{dispatch.site_fdt_cluster_link_name}\" "
            f"Located at \"{dispatch.interception_location}\" has been closed."
        )
        message = (
            f"Please note that Core Provisioning Request "
            f"\"{dispatch.site_fdt_cluster_link_name}\" located at "
            f"\"{dispatch.interception_location}\" "
            f"has been closed with the following comments:\n\n"
            f"\"{comment_content}\".\n\n"
            f"Click here for details: {full_url}.\n\nMashauri | Core."
        )
        return subject, message
    elif action == "reassign":
        subject = (
            f"Core Provisioning: \"{dispatch.site_fdt_cluster_link_name}\" "
            f"has been reassigned."
        )
        message = (
            f"Please note that Core Provisioning for "
            f"\"{dispatch.site_fdt_cluster_link_name}\" located at "
            f" \"{dispatch.interception_location}\" "
            f"has been reassigned.\n\n"
            f"Click here for details: {full_url}.\n\nMashauri | Core."
        )
    else:
        raise ValueError("Invalid action type provided for email preparation.")

    return subject, message


# Handler for adding comments
def handle_comment_update(request, dispatch, user, email_recipients, full_url):
    comment_content = request.POST['comment']
    dispatch_image = request.FILES.get('comment_image')
    if dispatch_image:
        save_dispatch_image(dispatch, dispatch_image)

    comment = Comment.objects.create(
        dispatch=dispatch,
        user=user,
        content=comment_content
    )
    comment.save()

    subject, message = prepare_email_details(
        dispatch, comment_content, full_url, "update")
    # send_mail(email_recipients, subject, message)

    return redirect('dispatch_detail', pk=dispatch.pk)


# Handler for closing dispatch
def handle_dispatch_closing(request, dispatch, email_recipients, full_url):
    comment_content = request.POST.get('comment')
    dispatch_image = request.FILES.get('close_image')
    if dispatch_image:
        save_dispatch_image(dispatch, dispatch_image)

    dispatch.status = "Closed"
    dispatch.closed_at = now()
    dispatch.save()

    comment = Comment.objects.create(
        dispatch=dispatch,
        user=request.user,
        content=comment_content
    )
    comment.save()

    messages.success(
        request,
        f"Dispatch for {dispatch.site_fdt_cluster_link_name} "
        f"(Lepton Project Name: {dispatch.lepton_project_name}) has been closed.")

    subject, message = prepare_email_details(
        dispatch, comment_content,
        full_url, "close")
    print(email_recipients)
    # send_mail(email_recipients, subject, message)

    return render(request, 'mashauri/success_deletion.html', {})


def handle_dispatch_reassignment(
        request, dispatch, email_recipients, full_url):
    selected_value = request.POST.get('assignment')
    if selected_value != 'ENTERPRISE CONNECTIVITY':
        dispatch.msp = selected_value
    else:
        dispatch.msp = None
    dispatch.reassign_to = selected_value
    dispatch.save()

    subject, message = prepare_email_details(
        dispatch, None, full_url, "reassign")
    # send_mail(email_recipients, subject, message)

    return render(request, 'mashauri/success_reassignment.html', {})


'''SENDING SCHEDULES EMAILS'''
def generate_pdf_mailed(dispatches, filename, title):
    buffer = BytesIO()

    # Create the PDF document in landscape mode
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(letter), rightMargin=36,
        leftMargin=36, topMargin=36, bottomMargin=36)

    # Create a custom stylesheet for text formatting
    styles = getSampleStyleSheet()
    header_style = styles['Heading1']
    header_style.fontName = "Times-Roman"
    header_style.fontSize = 16
    header_style.alignment = 1
    header_style.spaceAfter = 12

    # Normal text style
    normal_style = styles['Normal']
    normal_style.fontName = "Times-Roman"
    normal_style.fontSize = 8

    # Prepare table data with headers
    data = [
        ["Client Name", "CI", "Building Name", "Project Type", "MSP"]
    ]

    # Alternate colors for stripes
    stripe_colors = [colors.lightgrey, colors.whitesmoke]

    # Add rows for the dispatches
    for dispatch in dispatches:
        row = [
            Paragraph(dispatch.interception_location or "N/A", normal_style),
            Paragraph(dispatch.site_fdt_cluster_link_name or "N/A", normal_style),
            Paragraph(dispatch.project_type or "N/A", normal_style),
            Paragraph(dispatch.msp or "N/A", normal_style),
        ]
        data.append(row)

    # Define column widths
    column_widths = [
        1.8 * inch,
        1.2 * inch,
        1.8 * inch, 1.8 * inch, 1.2 * inch]

    # Create the table
    table = Table(data, colWidths=column_widths)

    # Apply styling to the table
    style = TableStyle([
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),  # White text for header
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),  # Dark blue header
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Center-align all cells
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),  # Grid lines
        ('FONTNAME', (0, 0), (-1, -1), 'Times-Roman'),  # Serif font
        ('FONTSIZE', (0, 0), (-1, 0), 10),  # Larger font for header
        ('FONTSIZE', (0, 1), (-1, -1), 8),  # Smaller font for body
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),  # Padding for header
        ('TOPPADDING', (0, 1), (-1, -1), 8),  # Padding for body rows
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('WORDWRAP', (0, 0), (-1, -1), True),  # Enable word wrapping
    ])

    # Apply striping colors for each row
    for i in range(1, len(data)):
        style.add('BACKGROUND', (0, i), (-1, i), stripe_colors[i % 2])

    # Apply the style to the table
    table.setStyle(style)

    # Add a title at the top of the page
    elements = [Paragraph(title, header_style)]  # Title at the top

    # Build the PDF document with the title and table
    doc.build(elements + [table])

    # Move to the beginning of the buffer to read the generated content
    buffer.seek(0)

    # Return as a ContentFile, including the dynamic filename
    return ContentFile(buffer.read(), name=filename)


def save_contentfile_to_disk(contentfile, filename):
    temp_file = tempfile.NamedTemporaryFile(
        delete=False, suffix=".pdf", mode='wb')
    with open(temp_file.name, 'wb') as f:
        f.write(contentfile.read())
    final_filename = f"{filename}.pdf"
    temp_file.close()
    os.rename(temp_file.name, final_filename)
    return final_filename


def send_escalation_email(start_time, end_time, subject, recipients):
    closed_dispatches = Dispatch.objects.filter(
        closed_at__range=(start_time, end_time))
    raised_dispatches = Dispatch.objects.filter(
        created_at__range=(start_time, end_time),
        status="Progress")

    if not closed_dispatches.exists() and not raised_dispatches.exists():
        print(
            f"No dispatches to notify for the time window: "
            f"{start_time} - {end_time}.")
        return

    # Generate PDFs for closed and expired dispatches
    closed_pdf = generate_pdf_mailed(
        closed_dispatches, "Closed Mashauri Escalations Report",
        "Closed Mashauri Escalations Report")
    raised_pdf = generate_pdf_mailed(
        raised_dispatches, "Raised Mashauri Escalations",
        "Raised Mashauri Escalations Report")

    closed_pdf_path = save_contentfile_to_disk(
        closed_pdf, "dispatch_report_closed")
    expired_pdf_path = save_contentfile_to_disk(
        raised_pdf, "dispatch_report_raised")

    # Send email with both PDFs as attachments
    if not closed_dispatches.exists() and not raised_dispatches.exists():
        print(
            f"No dispatches to notify for the time window: "
            f"{start_time} - {end_time}.")
        return

    # Format the times as per the requested format
    start_time_str = start_time.strftime("%B %d, %Y at %I:%M %p")
    end_time_str = end_time.strftime("%B %d, %Y at %I:%M %p")

    # Construct the message with formatted start and end times
    message = (
        f"The following escalations were updated between "
        f"{start_time_str} and {end_time_str}:\n\n"
    )

    # send_mail(
    #     recipients=recipients,
    #     subject=subject,
    #     message=message,
    #     attachment_path=[closed_pdf_path, expired_pdf_path]
    # )
    print(f"Email sent for {subject} covering {start_time} to {end_time}.")


def email_recipients_report():
    return [
        "sogola@safaricom.co.ke",
        "vmulongo@safaricom.co.ke",
        "mmutemi@safaricom.co.ke",
        "nirungu@safaricom.co.ke",
        "ckimani2@safaricom.co.ke",
        "condiere@safaricom.co.ke",
        "FixedNetworkSolutionsPlanning@Safaricom.co.ke",
        "HomeImplementation@Safaricom.co.ke",
        "HomeFixedWirelessAccess@Safaricom.co.ke",
        "FixedCapacityOptimization@Safaricom.co.ke"]


def schedule_six_pm_emails_mashauri_fixed():
    now_time = now()
    
    start_time = now_time.replace(
        hour=18, minute=1, second=0, microsecond=0
    ) - timedelta(days=1)

    end_time = now_time.replace(
        hour=17, minute=59, second=59, microsecond=0
    )

    recipients = email_recipients_report()
    send_escalation_email(
        start_time, end_time, "6 PM Escalation Update", recipients
    )
