from django.contrib import admin
from .models import ContentPlan, PlannedItem, Post, PostImage

admin.site.register(ContentPlan)
admin.site.register(PlannedItem)
admin.site.register(Post)
admin.site.register(PostImage)
