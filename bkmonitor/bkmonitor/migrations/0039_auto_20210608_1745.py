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
# Generated by Django 1.11.23 on 2021-06-08 09:45
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bkmonitor", "0038_auto_20210608_1656"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="dutyarrange",
            options={"verbose_name": "告警组时间安排", "verbose_name_plural": "告警组时间安排"},
        ),
        migrations.RenameField(
            model_name="usergroup",
            old_name="message",
            new_name="desc",
        ),
        migrations.AlterField(
            model_name="dutyarrange",
            name="user_group_id",
            field=models.IntegerField(db_index=True, verbose_name="关联的告警组"),
        ),
        migrations.AlterModelTable(
            name="dutyarrange",
            table="duty_arrange",
        ),
    ]