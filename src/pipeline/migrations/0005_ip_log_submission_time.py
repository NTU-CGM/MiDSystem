# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-12-27 14:10
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('pipeline', '0004_remove_user_job_gene_pred_assessment_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='ip_log',
            name='submission_time',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
