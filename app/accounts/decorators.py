from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from accounts.models import Profile


def recruiter_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        if profile.role != Profile.Role.RECRUITER:
            messages.error(request, 'Этот раздел доступен только рекрутерам.')
            return redirect('vacancy_list')
        return view_func(request, *args, **kwargs)
    return wrapper
