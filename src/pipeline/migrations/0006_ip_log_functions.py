# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-12-27 14:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pipeline', '0005_ip_log_submission_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='ip_log',
            name='functions',
            field=models.CharField(default='NA', max_length=25),
        ),
    ]