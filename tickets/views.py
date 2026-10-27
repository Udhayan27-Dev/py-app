from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from .models import SupportTicket

def staff_tickets_dashboard(request):
    """
    Staff-only dashboard listing support tickets with status updates.
    Returns custom 403 page if user is not staff.
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        return render(request, 'errors/403.html', {
            'error_code': '403',
            'error_title': 'Forbidden - Staff Only',
            'error_message': 'You must be a staff member or administrator to access the Support Tickets dashboard.'
        }, status=403)

    status_filter = request.GET.get('status', 'all')
    tickets = SupportTicket.objects.all().order_by('-created_at')

    if status_filter in ('open', 'in_progress', 'closed'):
        tickets = tickets.filter(status=status_filter)

    counts = {
        'all': SupportTicket.objects.count(),
        'open': SupportTicket.objects.filter(status='open').count(),
        'in_progress': SupportTicket.objects.filter(status='in_progress').count(),
        'closed': SupportTicket.objects.filter(status='closed').count(),
    }

    return render(request, 'tickets/staff_dashboard.html', {
        'tickets': tickets,
        'current_status': status_filter,
        'counts': counts,
    })


@require_POST
def update_ticket_status(request, pk):
    """
    Update status of a support ticket (open, in_progress, closed).
    Staff only.
    """
    if not request.user.is_authenticated or not request.user.is_staff:
        return render(request, 'errors/403.html', {
            'error_code': '403',
            'error_title': 'Forbidden - Staff Only',
            'error_message': 'Staff privileges required.'
        }, status=403)

    ticket = get_object_or_404(SupportTicket, pk=pk)
    new_status = request.POST.get('status')

    if new_status in ('open', 'in_progress', 'closed'):
        ticket.status = new_status
        ticket.save()
        messages.success(request, f"Ticket #{ticket.id} updated to {new_status.replace('_', ' ').title()}.")

    next_url = request.POST.get('next', '/staff/tickets/')
    return redirect(next_url)
