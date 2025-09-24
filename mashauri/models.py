from django.db import models
from django.contrib.auth.models import AbstractBaseUser, \
    UserManager, PermissionsMixin
from django.utils import timezone
from datetime import timedelta, datetime


class CustomUserManager(UserManager):
    def _create_user(self, username, password, **extra_fields):
        if not username:
            raise ValueError("You must provide a username")
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_active', True)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, username=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self._create_user(username, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        MSP = "MSP", "MSP"
        ENTERPRISE_CONNECTIVITY = (
            "ENTERPRISE CONNECTIVITY", "ENTERPRISE CONNECTIVITY")
        ENTERPRISE_PROJECT = "ENTERPRISE_PROJECT", "ENTERPRISE_PROJECT"
        SUPPORT = "SUPPORT", "SUPPORT"
        ROLLOUT_PARTNER = "ROLLOUT_PARTNER", "ROLLOUT_PARTNER"

    class MSP(models.TextChoices):
        No_msp = "None", "None"
        Egypro = "Egypro", "Egypro"
        Camusat = "Camusat", "Camusat"
        Adrian = "Adrian", "Adrian"
        Kinde = "Kinde", "Kinde"
        Fireside = "Fireside", "Fireside"
        Soliton = "Soliton", "Soliton"

    class RP(models.TextChoices):
        No_rp = "None", "None"
        Fireside = "Fireside", "Fireside"
        Kinde = "Kinde", "Kinde"
        Hatikvah = "Hatikvah", "Hatikvah"
        Camusat = "Camusat", "Camusat"
        Techminds = "Techminds", "Techminds"
        Egypro = "Egypro", "Egypro"
        Optimax = "Optimax", "Optimax"
        Pavicon = "Pavicon", "Pavicon"
        Decko = "Decko", "Decko"
        Adrian = "Adrian", "Adrian"
        Powergen = "Powergen", "Powergen"
        Tetranet = "Tetranet", "Tetranet"
        Extra_Dimensions = "Extra Dimensions", "Extra Dimensions"
        Quavatel = "Quavatel", "Quavatel"
        Acl = "Acl", "Acl"
        Blockchain = "Blockchain", "Blockchain"
        Huawei = "Huawei", "Huawei"
        Nextgen = "Nextgen", "Nextgen"
        Geonet = "Geonet", "Geonet"

    base_role = Role.ADMIN
    username = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=50, blank=True, default="")
    first_name = models.CharField(max_length=50, blank=True, default="")
    last_name = models.CharField(max_length=50, blank=True, default="")
    email = models.EmailField(blank=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(blank=True, null=True)
    role = models.CharField(max_length=50, choices=Role.choices)
    msp_category = models.CharField(
        max_length=50, choices=MSP.choices,
        default=MSP.No_msp, blank=False, null=True)
    rp_category = models.CharField(
        max_length=50, choices=RP.choices,
        default=RP.No_rp, blank=False, null=True)

    objects = CustomUserManager()
    USERNAME_FIELD = 'username'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        db_table = 'mashauri_users'

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.email.split('@')[0]


class Dispatch(models.Model):

    PROJECT_TYPE_CHOICES = [
        ('Metro 2G/ SDC', 'Metro 2G/ SDC'),
        ('FTTx - Low Cost', 'FTTx - Low Cost'),
        ('FTTx - ABR', 'FTTx - ABR'),
        ('FTTB', 'FTTB'),
        ('FTTx - Connections', 'FTTx - Connections'),
        ('Fixes/ Relocations', 'Fixes/ Relocations'),
        ('Existing Route - GPON', 'Existing Route - GPON'),
        ('Existing Route - Access/Agg/BB', 'Existing Route - Access/Agg/BB'),
    ]

    MSP_CHOICES = [
        ('None', 'None'),
        ('Egypro', 'Egypro'),
        ('Camusat', 'Camusat'),
        ('Adrian', 'Adrian'),
        ('Kinde', 'Kinde'),
        ('Fireside', 'Fireside'),
        ('Soliton', 'Soliton'),
    ]

    STATUS_CHOICES = [
        ('Hold', 'Hold'),
        ('Progress', 'Progress'),
        ('Closed', 'Closed'),
    ]

    EC_CHOICES = [
        ('Steven Ogola', 'Steven Ogola'),
        ('Emmanuel Muteti', 'Emmanuel Muteti'),
        ('Paul Msava', 'Paul Msava'),
        ('Kevin Waswa', 'Kevin Waswa'),
    ]

    RP_CHOICES = [
        ('None', 'None'),
        ('Fireside', 'Fireside'),
        ('Kinde', 'Kinde'),
        ('Hatikvah', 'Hatikvah'),
        ('Camusat', 'Camusat'),
        ('Techminds', 'Techminds'),
        ('Egypro', 'Egypro'),
        ('Optimax', 'Optimax'),
        ('Pavicon', 'Pavicon'),
        ('Decko', 'Decko'),
        ('Adrian', 'Adrian'),
        ('Powergen', 'Powergen'),
        ('Tetranet', 'Tetranet'),
        ('Extra Dimensions', 'Extra Dimensions'),
        ('Quavatel', 'Quavatel'),
        ('Acl', 'Acl'),
        ('Blockchain', 'Blockchain'),
        ('Huawei', 'Huawei'),
        ('Nextgen', 'Nextgen'),
        ('Geonet', 'Geonet'),
    ]

    site_fdt_cluster_link_name = models.CharField(max_length=50)
    lepton_project_name = models.CharField(max_length=50, null=True, blank=True)
    msp = models.CharField(
        max_length=50,
        choices=MSP_CHOICES, default=None, null=True)
    rp = models.CharField(max_length=50, choices=RP_CHOICES)
    # ec = models.CharField(
    #     max_length=50,
    #     choices=EC_CHOICES, default='Steven Ogola')
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES, default='Progress')
    project_type = models.CharField(
        max_length=50,
        choices=PROJECT_TYPE_CHOICES,
        default='FTTx - Low Cost'
    )
    comments = models.TextField(null=True, blank=True)
    site_fdt_location = models.CharField(max_length=255, null=True, blank=True)
    interception_location = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_expired = models.BooleanField(default=False, db_index=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    sla_timer = models.DateTimeField(null=True, blank=True)
    ticketing = models.OneToOneField(
        'Ticket', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='dispatch')
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True, blank=True)
    reassign_to = models.CharField(
        max_length=50, null=True,
        default=None, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    fdd_image = models.ImageField(upload_to='fdd_images/', null=True, blank=True)
    hld_image = models.ImageField(upload_to='hld_images/', null=True, blank=True)
    need_by_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date by which the dispatch is required"
    )
    implementation_contact_person = models.CharField(
        max_length=100,
        default="Unassigned",
        help_text="Person responsible for implementation"
    )

    def __str__(self):
        return f'{self.id} - {self.site_fdt_cluster_link_name}'

    def save(self, *args, **kwargs):
        if not self.id:
            if self.need_by_date:
                self.sla_timer = timezone.make_aware(
                    datetime.combine(self.need_by_date, datetime.min.time())
                ) + timedelta(hours=48)
            else:
                self.sla_timer = timezone.now() + timedelta(hours=48)

        super(Dispatch, self).save(*args, **kwargs)

    class Meta:
        db_table = 'mashauri_dispatches'
        verbose_name_plural = 'Dispatches'


class DispatchImage(models.Model):
    dispatch = models.ForeignKey(
        Dispatch, on_delete=models.CASCADE,
        related_name='images')
    image = models.ImageField(upload_to='dispatch_images/')
    image_type = models.CharField(max_length=50, default='creation')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Image for Dispatch {self.dispatch.id} - {self.image_type}'

    class Meta:
        db_table = 'mashauri_dispatch_images'
        verbose_name = 'Dispatch Image'
        verbose_name_plural = 'Dispatch Images'


class Ticket(models.Model):
    STATUS_CHOICES = [
        ('Open', 'Open'),
        ('In Progress', 'In Progress'),
        ('Closed', 'Closed'),
    ]
    dispatching = models.OneToOneField(Dispatch, on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(
        User, on_delete=models.CASCADE,
        null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    name = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f'Ticket for Dispatch ID: {self.dispatch.id}'

    class Meta:
        db_table = 'mashauri_tickets'


class SLA(models.Model):
    dispatch = models.ForeignKey(Dispatch, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    def __str__(self):
        return f'SLA for Dispatch ID: {self.dispatch.id}'

    class Meta:
        db_table = 'mashauri_SLAs'
        verbose_name = 'SLA'
        verbose_name_plural = 'SLAs'


class Comment(models.Model):
    dispatch = models.ForeignKey(Dispatch, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Comment by {self.user.username} on {self.created_at}'

    class Meta:
        db_table = 'mashauri_dispatch_comments'
        verbose_name = 'Dispatch Comment'
        verbose_name_plural = 'Dispatch Comments'
