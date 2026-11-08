from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.contrib import messages


def is_hoc_vien(user):
    """Kiểm tra tài khoản người dùng có quyền Học viên hợp lệ hay không.
    Theo đặc tả: tài khoản đang hoạt động (is_active=True), đã đăng nhập,
    và thuộc nhóm 'HOC_VIEN' (hoặc là staff/superuser để hỗ trợ kiểm thử/quản trị).
    """
    if not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name="HOC_VIEN").exists()


def hoc_vien_required(view_func):
    """Decorator bảo vệ các endpoint của Học viên.
    Nếu chưa đăng nhập: chuyển hướng đến trang đăng nhập.
    Nếu đã đăng nhập nhưng chưa được cấp quyền HOC_VIEN: hiển thị trang chờ cấp quyền (E1).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            resolver = getattr(request, "resolver_match", None)
            if resolver and hasattr(resolver, "app_names") and "login" in resolver.app_names:
                return redirect("login")
            return redirect("/admin/login/")
        
        if not is_hoc_vien(request.user):
            # E1: Thông báo chờ cấp quyền Học viên
            return render(
                request,
                "core/waiting_approval.html",
                {
                    "message": "Tài khoản của bạn đang chờ Quản trị viên phê duyệt quyền Học viên vào Group HOC_VIEN trước khi có thể truy cập nội dung luyện tập."
                },
                status=403,
            )
        return view_func(request, *args, **kwargs)

    return _wrapped_view
