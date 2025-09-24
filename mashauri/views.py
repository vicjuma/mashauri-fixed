import os
# from django.core.serializers import serialize
import plotly.graph_objs as go
import openpyxl
from django.urls import reverse
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import User, Dispatch, Comment
from datetime import timedelta
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from collections import defaultdict
from functools import wraps
from .utils import build_context, extract_dispatch_data, \
    save_dispatch, save_dispatch_image, create_ticket_and_pdf, \
    build_escalation_url, determine_email_recipients, \
    send_notification_email, handle_comment_update, \
    handle_dispatch_closing, handle_dispatch_reassignment, rename_uploaded_file


def unauthenticated_user(view_func):
    @wraps(view_func)
    def wrapper_func(request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.user.role == User.Role.ADMIN:
                return redirect('admin_dashboard')
            elif request.user.role == User.Role.MSP:
                return redirect('msp_dashboard')
            elif request.user.role == User.Role.ENTERPRISE_CONNECTIVITY:
                return redirect('ec_dashboard')
            elif request.user.role == User.Role.ENTERPRISE_PROJECT:
                return redirect('ep_dashboard')
            elif request.user.role == User.Role.SUPPORT:
                return redirect('support_dashboard')
            else:
                return view_func(request, *args, **kwargs)
    return wrapper_func


def calculate_time_remaining(datetime_value):
    now = timezone.now()
    remaining_time = datetime_value - now

    if remaining_time < timedelta(0):
        time_since_expired = now - datetime_value
        hours = time_since_expired.seconds // 3600
        minutes = (time_since_expired.seconds % 3600) // 60
        return f"Expired {hours} hours {minutes} minutes ago"

    # Calculate hours and minutes remaining
    hours = remaining_time.seconds // 3600
    minutes = (remaining_time.seconds % 3600) // 60

    return f"{hours} hours {minutes} minutes remaining"


@csrf_exempt
def user_login(request):
    if request.user.is_authenticated:
        if request.user.role == User.Role.ADMIN:
            return redirect('admin_dashboard')
        elif request.user.role == User.Role.MSP:
            return redirect('msp_dashboard')
        elif request.user.role == User.Role.ENTERPRISE_CONNECTIVITY:
            return redirect('ec_dashboard')
        elif request.user.role == User.Role.ENTERPRISE_PROJECT:
            return redirect('ep_dashboard')
        elif request.user.role == User.Role.SUPPORT:
            return redirect('support_dashboard')
        elif request.user.role == User.Role.ROLLOUT_PARTNER:
            return redirect('rp_dashboard')

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        if not username or not password:
            return JsonResponse(
                {'status': 'error',
                 'message': 'Username and password are required'}, status=400)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return JsonResponse(
                {'status': 'error',
                 'message': 'Invalid username or password'}, status=401)

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                request.session['userRole'] = request.user.role
                return JsonResponse(
                    {'status': 'success',
                     'role': request.user.role}, status=200)
            else:
                return JsonResponse(
                    {'status': 'error',
                     'message': 'User account is inactive'}, status=403)
        else:
            return JsonResponse(
                {'status': 'error',
                 'message': 'Invalid username or password'}, status=401)
    return render(request, 'mashauri/index.html', {})


@login_required
def msp_dashboard(request):
    user = request.user
    context = build_context(user, 'msp', user.msp_category, request)
    return render(request, 'mashauri/msp_dashboard.html', context)


@login_required
def ec_dashboard(request):
    user = request.user
    context = build_context(user, None, None, request)
    return render(request, 'mashauri/ec_dashboard.html', context)


@login_required
# @unauthenticated_user
def ep_dashboard(request):
    user = request.user
    context = build_context(user, None, None, request)
    return render(request, 'mashauri/ep_dashboard.html', context)


@login_required
# @unauthenticated_user
def support_dashboard(request):
    user = request.user
    context = build_context(user, None, None, request)
    return render(request, 'mashauri/support_dashboard.html', context)


@login_required
# @unauthenticated_user
def rp_dashboard(request):
    user = request.user
    context = build_context(user, 'rp', user.rp_category, request)
    return render(request, 'mashauri/rp_dashboard.html', context)


@login_required
@csrf_exempt
def dispatch(request):
    if request.method == 'POST':
        data = extract_dispatch_data(request)
        dispatch_instance = save_dispatch(data, request.user)

        val, ticket = create_ticket_and_pdf(dispatch_instance, data)
        escalation_url = build_escalation_url(request, dispatch_instance.id)
        email_recipients = determine_email_recipients(
            data['msp'], data['rp'])

        send_notification_email(
            project_type=data['project_type'],
            recipients=email_recipients,
            site_fdt_cluster_link_name=data['site_fdt_cluster_link_name'],
            interception_location=data['interception_location'],
            msp=data['msp'],
            rp=data['rp'],
            full_url=escalation_url,
            attachment_path=os.path.join(settings.MEDIA_ROOT, ticket.name)
        )

        return JsonResponse(
            {'status': 'success',
             'role': request.user.role}, status=200)

    context = {
        'msp_choices': Dispatch.MSP_CHOICES,
        'project_choices': Dispatch.PROJECT_TYPE_CHOICES,
        'rp_choices': Dispatch.RP_CHOICES
    }
    return render(request, 'mashauri/dispatch.html', context)


@login_required
@csrf_exempt
def dispatch_detail(request, pk):
    dispatch = get_object_or_404(Dispatch, pk=pk)
    current_user = request.user
    full_url = request.build_absolute_uri(
        reverse('dispatch_detail', kwargs={'pk': pk}))
    email_recipients = determine_email_recipients(
        dispatch.msp, dispatch.rp)
    print(email_recipients)

    if request.method == 'POST':
        # Handle comment-only POST request
        if 'comment_only' in request.POST:
            return handle_comment_update(
                request, dispatch, current_user, email_recipients, full_url)

        # Handle dispatch closing POST request
        elif 'close' in request.POST:
            return handle_dispatch_closing(
                request, dispatch, email_recipients, full_url)

        # Handle reassignment POST request
        elif 'reassign' in request.POST:
            return handle_dispatch_reassignment(
                request, dispatch, email_recipients, full_url)

    # Fetch and render dispatch details
    comments = Comment.objects.filter(
        dispatch=dispatch).order_by('-created_at')
    filtered_image = dispatch.images.filter(image_type='creation').first()

    def is_pdf(image):
        if not image or not hasattr(image, "image") or not hasattr(image.image, "url"):
            return False  # Return False if image is None or missing attributes
        return image.image.url.lower().endswith('.pdf')
    
    is_img_pdf = is_pdf(filtered_image)
    print(is_img_pdf)
    return render(request, 'mashauri/dispatch_details.html', {
        'dispatch': dispatch,
        'is_msp': current_user.role == 'MSP',
        'is_ec': current_user.role == 'ENTERPRISE CONNECTIVITY',
        'comments': comments,
        'msp_choices': Dispatch.MSP_CHOICES,
        'user': current_user,
        'image': filtered_image,
        'is_img_pdf': is_img_pdf,
    })


def plots_visualization(request):
    all_dispatches = Dispatch.objects.all().order_by('created_at')
    dispatch_numbers = list(range(1, len(all_dispatches) + 1))
    dispatch_counts = [idx + 1 for idx in range(len(all_dispatches))]

    # Plot: Dispatch Growth Over Time
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dispatch_numbers,
        y=dispatch_counts,
        mode='lines+markers', name='Dispatch Growth'))
    fig.update_layout(
        title='Dispatch Growth Over Time',
        xaxis_title='Number of Dispatches',
        yaxis_title='Cumulative Count',
        width=800,
        height=600
    )

    # Convert the Plotly figure to JSON
    plot_div = fig.to_html(full_html=False, config={'staticPlot': True})

    # Total escalations and aggregations for MSP
    total_escalations = 0
    msp_escalations = defaultdict(int)

    for dispatch in all_dispatches:
        if dispatch.project_type:
            total_escalations += 1
            msp_escalations[dispatch.msp] += 1

    msp_escalations = dict(msp_escalations)

    # MSP Bar Chart
    fig_msp = go.Figure()
    fig_msp.add_trace(go.Bar(
        name='Escalations to MSP',
        x=list(msp_escalations.keys()), y=list(msp_escalations.values()),
        marker_color='skyblue'))
    fig_msp.update_layout(
        title='Escalations to Each MSP',
        xaxis_title='MSP',
        yaxis_title='Count',
        width=800,
        height=600
    )
    plot_div_msp = fig_msp.to_html(
        full_html=False, config={'staticPlot': True})

    # Escalation Types Bar Chart
    escalation_type_counts = defaultdict(int)
    for dispatch in all_dispatches:
        escalation_type_counts[dispatch.project_type] += 1
    escalation_type_counts = dict(escalation_type_counts)

    fig_esc = go.Figure()
    fig_esc.add_trace(go.Bar(
        x=list(escalation_type_counts.keys()),
        y=list(escalation_type_counts.values()),
        marker_color='royalblue'))
    fig_esc.update_layout(
        title='Number of Escalations by Project Type',
        xaxis_title='Project Type',
        yaxis_title='Count',
        width=800,
        height=600
    )
    plot_div_esc = fig_esc.to_html(
        full_html=False, config={'staticPlot': True})

    # --- Average SLA per Project Type ---
    sla_durations = defaultdict(float)  # Total SLA durations
    sla_counts = defaultdict(int)  # Escalation counts

    for dispatch in all_dispatches:
        if dispatch.project_type and dispatch.sla_timer:
            # Calculate SLA duration in hours
            duration = (
                dispatch.sla_timer - dispatch.created_at
                ).total_seconds() / 3600
            sla_durations[dispatch.project_type] += duration
            sla_counts[dispatch.project_type] += 1

    # Calculate average SLA
    average_sla = {etype: sla_durations[etype] / sla_counts[etype]
                   for etype in sla_durations if sla_counts[etype] > 0}

    # SLA Bar Chart
    fig_sla = go.Figure()
    fig_sla.add_trace(go.Bar(
        x=list(average_sla.keys()),
        y=list(average_sla.values()),
        marker_color='green'))
    fig_sla.update_layout(
        title='Average SLA Hours by Project Type',
        xaxis_title='Project Type',
        yaxis_title='Average SLA (Hours)',
        width=800,
        height=600
    )
    plot_div_sla = fig_sla.to_html(
        full_html=False, config={'staticPlot': True})

    # Context
    context = {
        'plot_div': plot_div,
        'plot_div_msp': plot_div_msp,
        'total_escalations': total_escalations,
        'plot_div_esc': plot_div_esc,
        'plot_div_sla': plot_div_sla  # New SLA Chart
    }
    return render(request, 'mashauri/presentation.html', context)


def logout_user(request):
    logout(request)
    return redirect('login')


@login_required
def redirect_to_dashboard(request):
    if request.user.role == User.Role.ADMIN:
        return redirect('admin_dashboard')
    elif request.user.role == User.Role.MSP:
        return redirect('msp_dashboard')
    elif request.user.role == User.Role.ENTERPRISE_CONNECTIVITY:
        return redirect('ec_dashboard')
    elif request.user.role == User.Role.ENTERPRISE_PROJECT:
        return redirect('ep_dashboard')
    elif request.user.role == User.Role.SUPPORT:
        return redirect('support_dashboard')
    elif request.user.role == 'ROLLOUT_PARTNER':
        return redirect('rp_dashboard')
    else:
        return HttpResponseForbidden("You don't have access to any dashboard.")


@login_required
def average_sla(request):
    all_dispatches = Dispatch.objects.all()
    sla_durations = defaultdict(float)
    sla_counts = defaultdict(int)

    for dispatch in all_dispatches:
        if dispatch.sla_timer and dispatch.created_at:
            duration_hours = (
                dispatch.sla_timer - dispatch.created_at
            ).total_seconds() / 3600 
            sla_durations[dispatch.project_type] += duration_hours
            sla_counts[dispatch.project_type] += 1

    def format_duration(hours):
        total_minutes = int(hours * 60)
        h, m = divmod(total_minutes, 60)
        return f"{h}h {m}m"

    average_sla = {
        project_type: format_duration(sla_durations[project_type] / sla_counts[project_type])
        for project_type in sla_durations if sla_counts[project_type] > 0
    }

    context = {
        'average_sla': average_sla 
    }

    return render(request, 'mashauri/average_sla.html', context)

def export_dispatches_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Dispatches"

    # headers
    headers = ["Ticket", "Site/FDT/Cluster/Link Name", "Lepton Project Name", 
               "Site/FDT Location", "Interception Location", "RP", 
               "Project Type", "MSP", "Created At", "SLA Timer", "Status"]
    ws.append(headers)

    # data
    for dispatch in Dispatch.objects.all():
        ws.append([
            dispatch.ticket.name if dispatch.ticket else "N/A",
            dispatch.site_fdt_cluster_link_name,
            dispatch.lepton_project_name,
            dispatch.site_fdt_location,
            dispatch.interception_location,
            dispatch.rp,
            dispatch.project_type,
            dispatch.msp,
            dispatch.created_at.strftime("%Y-%m-%d %H:%M"),
            dispatch.sla_timer.strftime("%Y-%m-%d %H:%M") if dispatch.sla_timer else "N/A",
            dispatch.status,
        ])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="dispatches.xlsx"'
    wb.save(response)
    return response
