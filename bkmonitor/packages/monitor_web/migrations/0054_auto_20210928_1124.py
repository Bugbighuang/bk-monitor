# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2021-09-28 03:24
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("monitor_web", "0053_merge_20210914_1447"),
    ]

    operations = [
        migrations.CreateModel(
            name="SceneModel",
            fields=[
                ("unique_id", models.BigAutoField(primary_key=True, serialize=False)),
                ("bk_biz_id", models.IntegerField(verbose_name="业务ID")),
                ("id", models.CharField(max_length=32, verbose_name="场景ID")),
                ("name", models.CharField(max_length=64, verbose_name="名称")),
                ("data_range", models.JSONField(default=list, verbose_name="数据范围")),
                ("view_order", models.JSONField(default=dict, verbose_name="视图顺序")),
            ],
            options={
                "verbose_name": "场景",
                "verbose_name_plural": "场景",
            },
        ),
        migrations.CreateModel(
            name="SceneViewModel",
            fields=[
                ("unique_id", models.BigAutoField(primary_key=True, serialize=False)),
                ("bk_biz_id", models.IntegerField(verbose_name="业务ID")),
                ("scene_id", models.CharField(max_length=32, verbose_name="场景ID")),
                ("id", models.CharField(max_length=32, verbose_name="视图ID")),
                ("name", models.CharField(max_length=64, verbose_name="名称")),
                ("variables", models.JSONField(default=list, verbose_name="变量配置")),
                (
                    "type",
                    models.CharField(
                        choices=[("overview", "概览"), ("detail", "详情")], max_length=16, verbose_name="视图类型"
                    ),
                ),
                (
                    "mode",
                    models.CharField(
                        choices=[("auto", "平铺"), ("custom", "自定义")], default="auto", max_length=16, verbose_name="模式"
                    ),
                ),
                ("order", models.JSONField(default=list, verbose_name="排序配置(平铺模式专用)")),
                ("panels", models.JSONField(default=list, verbose_name="图表配置")),
                ("list", models.JSONField(default=list, verbose_name="列表页配置")),
                ("options", models.JSONField(default=dict, verbose_name="配置项")),
            ],
            options={
                "verbose_name": "场景视图",
                "verbose_name_plural": "场景视图",
            },
        ),
        migrations.CreateModel(
            name="SceneViewOrderModel",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("bk_biz_id", models.IntegerField(verbose_name="业务ID")),
                ("scene_id", models.CharField(max_length=32, verbose_name="场景ID")),
                (
                    "type",
                    models.CharField(choices=[("overview", "概览"), ("detail", "详情")], max_length=16, verbose_name="类型"),
                ),
                ("config", models.JSONField(default=list, verbose_name="排序配置")),
            ],
            options={
                "verbose_name": "场景视图排序",
                "verbose_name_plural": "场景视图排序",
            },
        ),
        migrations.AlterUniqueTogether(
            name="sceneviewordermodel",
            unique_together={("bk_biz_id", "scene_id", "type")},
        ),
        migrations.AlterIndexTogether(
            name="sceneviewordermodel",
            index_together={("bk_biz_id", "scene_id", "type")},
        ),
        migrations.AlterUniqueTogether(
            name="sceneviewmodel",
            unique_together={("bk_biz_id", "scene_id", "type", "id")},
        ),
        migrations.AlterIndexTogether(
            name="sceneviewmodel",
            index_together={("bk_biz_id", "scene_id", "type", "id")},
        ),
        migrations.AlterUniqueTogether(
            name="scenemodel",
            unique_together={("bk_biz_id", "id")},
        ),
    ]