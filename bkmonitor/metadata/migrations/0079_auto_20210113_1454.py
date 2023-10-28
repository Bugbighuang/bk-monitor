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
# Generated by Django 1.11.23 on 2021-01-13 06:54


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("metadata", "0078_auto_20201201_1521"),
    ]

    operations = [
        migrations.AddField(
            model_name="influxdbtaginfo",
            name="force_overwrite",
            field=models.BooleanField(default=False, verbose_name="是否强制写入"),
        ),
        migrations.AddField(
            model_name="influxdbtaginfo",
            name="manual_unreadable_host",
            field=models.CharField(blank=True, default="", max_length=128, null=True, verbose_name="静态不可读机器"),
        ),
    ]