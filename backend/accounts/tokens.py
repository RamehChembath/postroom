from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """A distinct key_salt from the default generator (used for password reset)
    means tokens from one flow can never validate for the other, even though
    both are built from the same user state."""
    key_salt = "postroom.accounts.email_verification"


email_verification_token = EmailVerificationTokenGenerator()
