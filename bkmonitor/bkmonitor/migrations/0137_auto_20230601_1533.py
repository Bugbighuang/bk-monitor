# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2023-06-01 07:33
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bkmonitor', '0136_merge_20230522_1157'),
    ]

    operations = [
        migrations.AddField(
            model_name='externalpermissionapplyrecord',
            name='approval_sn',
            field=models.CharField(blank=True, default='', max_length=128, null=True, verbose_name='审批单号'),
        ),
        migrations.AddField(
            model_name='externalpermissionapplyrecord',
            name='approval_url',
            field=models.CharField(blank=True, default='', max_length=1024, null=True, verbose_name='审批地址'),
        ),
        migrations.AddField(
            model_name='externalpermissionapplyrecord',
            name='status',
            field=models.CharField(
                choices=[
                    ('no_status', 'no_status'),
                    ('approval', 'approval'),
                    ('success', 'success'),
                    ('failed', 'failed'),
                ],
                default='no_status',
                max_length=32,
                verbose_name='状态',
            ),
        ),
    ]