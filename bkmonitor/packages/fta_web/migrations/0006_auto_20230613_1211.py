# Generated by Django 3.2.15 on 2023-06-13 04:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('fta_web', '0005_auto_20230222_1548'),
    ]

    operations = [
        migrations.DeleteModel(
            name='AlarmApplication',
        ),
        migrations.DeleteModel(
            name='AlarmDef',
        ),
        migrations.DeleteModel(
            name='AlarmType',
        ),
        migrations.DeleteModel(
            name='Solution',
        ),
    ]