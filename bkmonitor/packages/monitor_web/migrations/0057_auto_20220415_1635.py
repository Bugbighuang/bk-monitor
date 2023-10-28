# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2022-04-15 08:35
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("monitor_web", "0056_auto_20220318_1040"),
    ]

    operations = [
        migrations.AlterField(
            model_name="importparse",
            name="type",
            field=models.CharField(
                choices=[("plugin", "插件配置"), ("collect", "采集配置"), ("strategy", "策略配置"), ("view", "视图配置")],
                max_length=100,
                verbose_name="配置类型",
            ),
        ),
    ]