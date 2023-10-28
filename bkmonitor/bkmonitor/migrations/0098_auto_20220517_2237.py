# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2022-05-17 14:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bkmonitor", "0097_merge_20220507_1703"),
    ]

    operations = [
        migrations.AddField(
            model_name="bcscluster",
            name="alert_status",
            field=models.CharField(default="enabled", max_length=32, verbose_name="告警状态"),
        ),
        migrations.AlterField(
            model_name="actioninstance",
            name="real_status",
            field=models.CharField(
                choices=[
                    ("received", "收到"),
                    ("waiting", "审批中"),
                    ("converging", "收敛中"),
                    ("sleep", "收敛处理等待"),
                    ("converged", "收敛结束"),
                    ("running", "处理中"),
                    ("success", "成功"),
                    ("partial_success", "部分成功"),
                    ("failure", "失败"),
                    ("partial_failure", "部分失败"),
                    ("skipped", "跳过"),
                    ("shield", "已屏蔽"),
                ],
                default="",
                max_length=64,
                verbose_name="真实执行状态",
            ),
        ),
        migrations.AlterField(
            model_name="actioninstance",
            name="status",
            field=models.CharField(
                choices=[
                    ("received", "收到"),
                    ("waiting", "审批中"),
                    ("converging", "收敛中"),
                    ("sleep", "收敛处理等待"),
                    ("converged", "收敛结束"),
                    ("running", "处理中"),
                    ("success", "成功"),
                    ("partial_success", "部分成功"),
                    ("failure", "失败"),
                    ("partial_failure", "部分失败"),
                    ("skipped", "跳过"),
                    ("shield", "已屏蔽"),
                ],
                default="received",
                max_length=64,
                verbose_name="执行状态",
            ),
        ),
    ]