from apps.users.models import CustomUser


class UserService:
    @staticmethod
    def create_user(email, password, nickname="", name="", phone_number=""):
        if CustomUser.objects.filter(email=email).exists():
            raise ValueError("Email already exists.")
        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            nickname=nickname,
            name=name,
            phone_number=phone_number,
        )
        return user

    @staticmethod
    def get_user_by_id(user_id):
        return CustomUser.objects.get(id=user_id)

    @staticmethod
    def update_user(user, data):
        for attr, value in data.items():
            setattr(user, attr, value)
        user.save()
        return user

    @staticmethod
    def delete_user(user):
        user.delete()
