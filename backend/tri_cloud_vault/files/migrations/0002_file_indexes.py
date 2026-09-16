from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("files", "0001_initial"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="file",
            index=models.Index(
                fields=["user", "-created_at"],
                name="file_user_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="file",
            index=models.Index(
                fields=["user", "aws_path"],
                name="file_user_aws_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="file",
            index=models.Index(
                fields=["user", "azure_path"],
                name="file_user_azure_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="file",
            index=models.Index(
                fields=["user", "gcp_path"],
                name="file_user_gcp_idx",
            ),
        ),
    ]