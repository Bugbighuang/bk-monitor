# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2021-09-27 03:53
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("metadata", "0091_merge_20210717_1517"),
    ]

    operations = [
        migrations.CreateModel(
            name="EsSnapshot",
            fields=[
                ("table_id", models.CharField(max_length=128, primary_key=True, serialize=False, verbose_name="结果表id")),
                (
                    "target_snapshot_repository_name",
                    models.CharField(default="", max_length=128, verbose_name="快照仓库名称"),
                ),
                ("snapshot_days", models.IntegerField(default=0, verbose_name="快照天数")),
                ("creator", models.CharField(max_length=32, verbose_name="创建者")),
                ("create_time", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("last_modify_user", models.CharField(max_length=32, verbose_name="最后更新者")),
                ("last_modify_time", models.DateTimeField(auto_now=True, verbose_name="最后更新时间")),
            ],
        ),
        migrations.CreateModel(
            name="EsSnapshotIndice",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("table_id", models.CharField(max_length=128, verbose_name="结果表id")),
                ("snapshot_name", models.CharField(max_length=150, verbose_name="快照名称")),
                ("cluster_id", models.IntegerField(verbose_name="集群id")),
                ("repository_name", models.CharField(max_length=128, verbose_name="所在仓库名称")),
                ("index_name", models.CharField(max_length=150, verbose_name="物理索引名称")),
                ("doc_count", models.BigIntegerField(verbose_name="文档数量")),
                ("store_size", models.BigIntegerField(verbose_name="索引大小")),
                ("start_time", models.DateTimeField(verbose_name="索引开始时间")),
                ("end_time", models.DateTimeField(verbose_name="索引结束时间")),
            ],
            options={
                "verbose_name": "快照物理索引记录",
                "verbose_name_plural": "快照物理索引记录",
            },
        ),
        migrations.CreateModel(
            name="EsSnapshotRepository",
            fields=[
                (
                    "repository_name",
                    models.CharField(max_length=128, primary_key=True, serialize=False, verbose_name="仓库名称"),
                ),
                ("cluster_id", models.IntegerField(verbose_name="集群id")),
                ("alias", models.CharField(max_length=128, verbose_name="仓库别名")),
                ("creator", models.CharField(max_length=32, verbose_name="创建者")),
                ("create_time", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("last_modify_user", models.CharField(max_length=32, verbose_name="最后更新者")),
                ("last_modify_time", models.DateTimeField(auto_now=True, verbose_name="最后更新时间")),
                ("is_deleted", models.BooleanField(default=False, verbose_name="仓库表是否已经禁用")),
            ],
            options={
                "verbose_name": "ES仓库记录表",
                "verbose_name_plural": "ES仓库记录表",
            },
        ),
        migrations.CreateModel(
            name="EsSnapshotRestore",
            fields=[
                ("restore_id", models.AutoField(primary_key=True, serialize=False, verbose_name="仓库id")),
                ("table_id", models.CharField(max_length=128, verbose_name="结果表id")),
                ("start_time", models.DateTimeField(verbose_name="开始时间")),
                ("end_time", models.DateTimeField(verbose_name="结束时间")),
                ("expired_time", models.DateTimeField(verbose_name="到期时间")),
                ("expired_delete", models.BooleanField(default=False, verbose_name="是否到期删除")),
                ("indices", models.TextField(verbose_name="索引文档列表")),
                ("complete_doc_count", models.BigIntegerField(default=0, verbose_name="回溯已经回溯完成的文档数量")),
                ("total_doc_count", models.BigIntegerField(verbose_name="回溯总的文档大小")),
                ("total_store_size", models.BigIntegerField(verbose_name="回溯索引的存储大小")),
                ("duration", models.IntegerField(default=-1, verbose_name="回溯持续时间")),
                ("creator", models.CharField(max_length=32, verbose_name="创建者")),
                ("create_time", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("last_modify_user", models.CharField(max_length=32, verbose_name="最后更新者")),
                ("last_modify_time", models.DateTimeField(auto_now=True, verbose_name="最后更新时间")),
                ("is_deleted", models.BooleanField(default=False, verbose_name="仓库表是否已经禁用")),
            ],
            options={
                "verbose_name": "ES回溯任务表",
                "verbose_name_plural": "ES回溯任务表",
            },
        ),
        migrations.AddField(
            model_name="esstorage",
            name="time_zone",
            field=models.IntegerField(default=0, verbose_name="时区设置"),
        ),
    ]