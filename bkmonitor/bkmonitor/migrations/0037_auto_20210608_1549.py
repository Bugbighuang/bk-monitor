# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸智云 - 监控平台 (BlueKing - Monitor) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
# Generated by Django 1.11.23 on 2021-06-08 07:49
from __future__ import unicode_literals

from django.db import migrations, models

import bkmonitor.middlewares.source


class Migration(migrations.Migration):

    dependencies = [
        ("bkmonitor", "0036_auto_20210608_0955"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserGroup",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_enabled", models.BooleanField(default=True, verbose_name="是否启用")),
                ("is_deleted", models.BooleanField(default=False, verbose_name="是否删除")),
                ("create_user", models.CharField(blank=True, default="", max_length=32, verbose_name="创建人")),
                ("create_time", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("update_user", models.CharField(blank=True, default="", max_length=32, verbose_name="最后修改人")),
                ("update_time", models.DateTimeField(auto_now=True, verbose_name="最后修改时间")),
                ("name", models.CharField(max_length=128, verbose_name="用户组名称")),
                ("bk_biz_id", models.IntegerField(blank=True, db_index=True, default=0, verbose_name="业务ID")),
                ("users", models.JSONField(default=dict, verbose_name="告警处理对象")),
                ("message", models.TextField(verbose_name="说明/备注")),
                (
                    "source",
                    models.CharField(
                        default=bkmonitor.middlewares.source.get_source_app_code, max_length=32, verbose_name="来源系统"
                    ),
                ),
            ],
            options={
                "verbose_name": "告警处理组配置",
                "verbose_name_plural": "告警处理组配置",
                "db_table": "user_group",
            },
        ),
        migrations.AlterIndexTogether(
            name="usergroup",
            index_together={("bk_biz_id", "source")},
        ),
    ]