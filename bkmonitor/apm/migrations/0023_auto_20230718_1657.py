# Generated by Django 3.2.15 on 2023-07-18 08:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("apm", "0022_ebpfapplicationconfig"),
    ]

    operations = [
        migrations.AddField(
            model_name="hostinstance",
            name="bk_host_id",
            field=models.IntegerField(null=True, verbose_name="主机ID"),
        ),
        migrations.AlterField(
            model_name="hostinstance",
            name="ip",
            field=models.CharField(max_length=1024, verbose_name="ipv4地址"),
        ),
    ]