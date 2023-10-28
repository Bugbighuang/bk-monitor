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
# Generated by Django 1.11.23 on 2021-07-30 09:54
from __future__ import unicode_literals

from django.db import migrations, models

import bkmonitor.utils.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ("bkmonitor", "0053_auto_20210710_1923"),
    ]

    operations = [
        migrations.AddField(
            model_name="actionplugin",
            name="description",
            field=models.TextField(blank=True, default="", verbose_name="详细描述，markdown文本"),
        ),
        migrations.AlterField(
            model_name="actioninstance",
            name="alert_level",
            field=models.IntegerField(choices=[(3, "提醒"), (2, "预警"), (1, "致命")], default=3, verbose_name="告警级别"),
        ),
        migrations.AlterField(
            model_name="actioninstance",
            name="strategy",
            field=bkmonitor.utils.db.fields.JsonField(default={}, verbose_name="策略快照"),
        ),
    ]