from rest_framework.exceptions import PermissionDenied, NotFound
from .models import Workspace


def get_workspace(request):
    """Resolves the workspace a request is acting on: the 'workspace' query param
    (used for GET/list) or the 'workspace' field in the request body (used for POST),
    and verifies the caller owns it. Every workspace-scoped endpoint relies on this —
    it's the one place avatar isolation is enforced."""
    ws_id = request.query_params.get("workspace") or request.data.get("workspace")
    if not ws_id:
        raise NotFound("A 'workspace' id is required.")
    try:
        ws = Workspace.objects.get(id=ws_id)
    except (Workspace.DoesNotExist, ValueError, TypeError):
        raise NotFound("Workspace not found.")
    if ws.owner_id != request.user.id:
        raise PermissionDenied("Not your workspace.")
    return ws
