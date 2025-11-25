# from django.contrib import admin
# from django.utils.html import format_html

# from .models import (
#     Factory, Staff, Material, MaterialGroup, MaterialVariant, DeliveryMethod
# )

# @admin.register(Factory)
# class FactoryAdmin(admin.ModelAdmin):
#     list_display = [
#         'name', 'email', 'is_active', 'created_at'
#     ]
#     list_filter = ['is_active', 'created_at']
#     search_fields = ['name', 'email', 'phone']
#     ordering = ['name']
#     readonly_fields = ['id', 'created_at', 'updated_at']

#     # fieldsets = (
#     #     ('Basic Information', {
#     #         'fields': ('name', 'email', 'phone', 'address')
#     #     }),
#     #     ('Factory Settings', {
#     #         'fields': (
#     #             'auto_assign_orders', 'require_qa_approval', 'default_priority',
#     #             'working_hours_start', 'working_hours_end', 'working_timezone'
#     #         )
#     #     }),
#     #     ('Notifications', {
#     #         'fields': (
#     #             'notify_order_assigned', 'notify_status_changes',
#     #             'notify_qa_failures', 'notify_deadlines'
#     #         )
#     #     }),
#     #     ('Capacity Settings', {
#     #         'fields': ('max_concurrent_orders', 'daily_order_limit')
#     #     }),
#     #     ('Status', {
#     #         'fields': ('is_active', 'deactivated_at', 'deactivation_reason', 'reactivated_at')
#     #     }),
#     #     ('Materials', {
#     #         'fields': ('materials',),
#     #         'classes': ('collapse',)
#     #     }),
#     # )
    
# # @admin.register(Staff)
# # class StaffAdmin(admin.ModelAdmin):
# #     list_display = [
# #         'fullname', 'email', 'employee_id', 'factory_name'
# #     ]

# # @admin.register(Material)
# # class MaterialAdmin(admin.ModelAdmin):
# #     list_display = [
# #         'name', 'variant_type', 'variants_count'
# #     ]
# #     list_filter = ['name', 'variant_type']
# #     search_fields = ['name']
# #     ordering = ['name']

# admin.site.register(Staff)
# admin.site.register(Material)
# admin.site.register(MaterialGroup)
# admin.site.register(MaterialVariant)
# admin.site.register(DeliveryMethod)