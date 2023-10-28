# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2021-11-24 10:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bkmonitor", "0073_merge_20211123_1526"),
    ]

    operations = [
        migrations.CreateModel(
            name="MetricMappingConfigModel",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("config_field", models.CharField(db_index=True, max_length=128, verbose_name="配置名称")),
                ("create_time", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("mapping_detail", models.JSONField(default=dict, verbose_name="映射信息")),
                ("mapping_range", models.JSONField(default=list, verbose_name="映射范围")),
                ("bk_biz_id", models.IntegerField(verbose_name="业务ID")),
            ],
            options={
                "verbose_name": "指标映射配置",
                "verbose_name_plural": "指标映射配置",
                "db_table": "metric_mapping_config",
            },
        ),
    ]