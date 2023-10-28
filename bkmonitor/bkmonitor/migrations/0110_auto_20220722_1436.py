# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2022-07-22 06:36
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bkmonitor", "0109_auto_20220706_1231"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="bcsmonitor",
            name="monitor_type",
        ),
        migrations.RemoveField(
            model_name="bcsmonitor",
            name="original_data",
        ),
        migrations.AlterField(
            model_name="actioninstance",
            name="signal",
            field=models.CharField(
                choices=[
                    ("manual", "手动"),
                    ("abnormal", "告警触发时"),
                    ("recovered", "告警恢复时"),
                    ("closed", "告警关闭时"),
                    ("no_data", "无数据时"),
                    ("collect", "汇总"),
                    ("execute", "执行动作时"),
                    ("execute_success", "执行成功时"),
                    ("execute_failed", "执行失败时"),
                    ("demo", "调试"),
                    ("unshielded", "解除屏蔽"),
                ],
                help_text="触发该事件的告警信号，如告警异常，告警恢复，告警关闭等",
                max_length=64,
                verbose_name="触发信号",
            ),
        ),
        migrations.AlterField(
            model_name="bcsmonitor",
            name="metric_interval",
            field=models.CharField(max_length=8),
        ),
        migrations.AlterField(
            model_name="bcsmonitor",
            name="metric_path",
            field=models.CharField(max_length=32),
        ),
        migrations.AlterField(
            model_name="bcsmonitor",
            name="metric_port",
            field=models.CharField(max_length=8),
        ),
        migrations.AlterIndexTogether(
            name="healthzmetricrecord",
            index_together={("server_ip", "metric_alias")},
        ),
    ]