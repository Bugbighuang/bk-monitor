# Generated by Django 3.2.15 on 2023-05-23 13:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('log_clustering', '0018_aiopssignatureandpattern_label'),
    ]

    operations = [
        migrations.AddField(
            model_name='clusteringconfig',
            name='log_count_agg_rt',
            field=models.CharField(blank=True, default='', max_length=255, null=True, verbose_name='日志数量聚合结果表'),
        ),
        migrations.AddField(
            model_name='clusteringconfig',
            name='model_output_rt',
            field=models.CharField(blank=True, default='', max_length=255, null=True, verbose_name='模型输出结果表'),
        ),
    ]