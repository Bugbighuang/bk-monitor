# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2022-03-22 07:17
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bkmonitor", "0081_merge_20220208_1522"),
    ]

    operations = [
        migrations.CreateModel(
            name="DutyArrangeSnap",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_group_id", models.IntegerField(db_index=True, verbose_name="告警组ID")),
                ("duty_arrange_id", models.IntegerField(db_index=True, verbose_name="轮值组ID")),
                ("next_plan_time", models.DateTimeField(null=True, verbose_name="配置生效时间")),
                ("first_effective_time", models.DateTimeField(null=True, verbose_name="配置生效时间")),
                ("duty_snap", models.JSONField(default=dict, verbose_name="当前快照的配置内容")),
                ("is_active", models.BooleanField(default=False, verbose_name="是否生效状态")),
            ],
            options={
                "verbose_name": "告警组时间安排快照",
                "verbose_name_plural": "告警组时间安排快照",
                "db_table": "duty_arrange_snap",
            },
        ),
        migrations.CreateModel(
            name="DutyPlan",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("user_group_id", models.IntegerField(db_index=True, verbose_name="关联的告警组")),
                ("duty_arrange_id", models.IntegerField(db_index=True, verbose_name="轮值组ID")),
                ("order", models.IntegerField(verbose_name="轮班组的顺序")),
                ("is_active", models.BooleanField(default=False, verbose_name="是否生效状态")),
                ("users", models.JSONField(default=dict, verbose_name="当前告警处理值班人员")),
                ("begin_time", models.DateTimeField(verbose_name="当前轮班生效开始时间")),
                ("end_time", models.DateTimeField(null=True, verbose_name="当前轮班生效结束时间")),
                ("duty_time", models.JSONField(default=dict, verbose_name="轮班时间安排")),
            ],
        ),
        migrations.RemoveField(
            model_name="dutyarrange",
            name="duty_type",
        ),
        migrations.RemoveField(
            model_name="dutyarrange",
            name="work_day",
        ),
        migrations.AddField(
            model_name="dutyarrange",
            name="backups",
            field=models.JSONField(default=dict, verbose_name="备份安排"),
        ),
        migrations.AddField(
            model_name="dutyarrange",
            name="duty_time",
            field=models.JSONField(default=dict, verbose_name="轮班时间安排"),
        ),
        migrations.AddField(
            model_name="dutyarrange",
            name="duty_users",
            field=models.JSONField(default=dict, verbose_name="轮班用户"),
        ),
        migrations.AddField(
            model_name="dutyarrange",
            name="effective_time",
            field=models.DateTimeField(db_index=True, null=True, verbose_name="配置生效时间"),
        ),
        migrations.AddField(
            model_name="dutyarrange",
            name="handoff_time",
            field=models.JSONField(default=dict, verbose_name="轮班交接时间安排"),
        ),
        migrations.AddField(
            model_name="dutyarrange",
            name="need_rotation",
            field=models.BooleanField(default=False, verbose_name="是否轮班"),
        ),
        migrations.AddField(
            model_name="dutyarrange",
            name="order",
            field=models.IntegerField(default=0, verbose_name="轮班组的顺序"),
        ),
        migrations.AlterField(
            model_name="dutyarrange",
            name="users",
            field=models.JSONField(default=dict, verbose_name="告警处理值班人员"),
        ),
        migrations.AlterField(
            model_name="shield",
            name="category",
            field=models.CharField(
                choices=[
                    ("scope", "范围屏蔽"),
                    ("strategy", "策略屏蔽"),
                    ("event", "事件屏蔽"),
                    ("alert", "告警屏蔽"),
                    ("dimension", "维度屏蔽"),
                ],
                max_length=32,
                verbose_name="屏蔽类型",
            ),
        ),
    ]