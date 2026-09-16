from django.urls import path
from .views import RegisterView,VerifyEmailView,LoginView,ResendVerificationEmailView,ForgotPasswordView,ResetPasswordView
urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("login/", LoginView.as_view(), name="login"),
    path("resend-verification/", ResendVerificationEmailView.as_view()),
    path("forgot-password/", ForgotPasswordView.as_view()),
    path("reset-password/", ResetPasswordView.as_view()),

]
