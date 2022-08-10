from rest_framework.serializers import ModelSerializer
from .models import User, Verification
from django.contrib.auth.models import Group


class GroupMiniSerializer(ModelSerializer):
    class Meta:
        model = Group
        fields = ["name"]


class UserMiniSerializer(ModelSerializer):

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "country_code",
            "phone_number",
            "unique_number",
            "is_active",
            "groups",
        ]

    def to_representation(self, instance):
        serialized_data = super(UserMiniSerializer, self).to_representation(instance)
        serialized_data['id'] = str(instance.id)
        serialized_data["has_password"] = instance.has_usable_password()
        groups_set = instance.groups.all()
        groups = []

        for g in groups_set:
            groups.append(g.name)
        serialized_data["groups"] = groups
        return serialized_data


class UserSerializer(ModelSerializer):

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "country_code",
            "phone_number",
            "unique_number",
            "is_active",
            "is_staff"
        ]

    def to_representation(self, instance):
        serialized_data = super(UserSerializer, self).to_representation(instance)
        serialized_data['id'] = str(instance.id)
        serialized_data["has_password"] = instance.has_usable_password()
        groups_set = instance.groups.all()
        groups = []

        for g in groups_set:
            groups.append(g.name)
        serialized_data["groups"] = groups

        perms_set = instance.user_permissions.all()
        perms = []

        for p in perms_set:
            perms.append(p.codename)
        serialized_data["user_permissions"] = perms
        return serialized_data


class VerificationSerializer(ModelSerializer):
    class Meta:
        model = Verification
        fields = "__all__"
