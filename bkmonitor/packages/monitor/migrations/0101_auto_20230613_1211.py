# Generated by Django 3.2.15 on 2023-06-13 04:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('monitor', '0100_auto_20230519_1738'),
    ]

    operations = [
        migrations.DeleteModel(
            name='AlarmStrategy',
        ),
        migrations.AlterModelOptions(
            name='application',
            options={},
        ),
    ]