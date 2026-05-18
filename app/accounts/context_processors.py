from .models import Profile


def user_role(request):
    if not request.user.is_authenticated:
        return {'is_recruiter': False}
    profile, _ = Profile.objects.get_or_create(user=request.user)
    return {'is_recruiter': profile.role == Profile.Role.RECRUITER}