from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    approvals,
    areas,
    audit,
    auth,
    cancellation_actions,
    closure_delegation,
    dashboard,
    direct_expenses,
    document_actions,
    expenses,
    financial_actions,
    iam,
    iam_access_policy,
    iam_group_assignments,
    iam_users,
    legacy_position_notifications,
    my_actions,
    organization_overview,
    position_access,
    quotation_actions,
    request_actions,
    revision_actions,
    rules,
    tracking,
    users,
)
from app.core.config import get_settings
from app.core.rate_limit import authenticated_subject, consume_user_request, password_reset_subject, policy_for_request
from app.core.security import require_permission
import app.models.activity_periods  # noqa: F401  Ensures temporal-history hooks are registered.


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Settings validation is the only startup responsibility. Database schema
    # changes and bootstrap operations run as deployment steps before the app.
    get_settings()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title='Approval Workflow API',
        version='0.2.0',
        lifespan=lifespan,
        docs_url='/api/docs',
        openapi_url='/api/openapi.json',
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    @app.middleware('http')
    async def limit_authenticated_users(request: Request, call_next):
        excluded = {'/api/health', '/api/auth/login', '/api/auth/activity'}
        if (
            request.method != 'OPTIONS'
            and request.url.path.startswith('/api/')
            and request.url.path not in excluded
        ):
            if request.url.path == '/api/auth/reset-password':
                subject = password_reset_subject(
                    request.client.host if request.client else None,
                    request.headers.get('x-forwarded-for'),
                )
            else:
                subject = authenticated_subject(request.headers.get('authorization'))
            if subject:
                policy = policy_for_request(request.method, request.url.path)
                allowed, remaining, retry_after = consume_user_request(subject, policy)
                if not allowed:
                    return JSONResponse(
                        status_code=429,
                        content={'detail': f'Máximo {policy.limit} acciones de tipo {policy.name} en {policy.window_seconds} segundos'},
                        headers={
                            'Retry-After': str(retry_after),
                            'X-RateLimit-Policy': policy.name,
                            'X-RateLimit-Limit': str(policy.limit),
                            'X-RateLimit-Remaining': '0',
                            'X-RateLimit-Window': str(policy.window_seconds),
                        },
                    )
                request.state.rate_limit_remaining = remaining
                request.state.rate_limit_policy = policy

        response = await call_next(request)
        if hasattr(request.state, 'rate_limit_remaining'):
            policy = request.state.rate_limit_policy
            response.headers['X-RateLimit-Policy'] = policy.name
            response.headers['X-RateLimit-Limit'] = str(policy.limit)
            response.headers['X-RateLimit-Remaining'] = str(request.state.rate_limit_remaining)
            response.headers['X-RateLimit-Window'] = str(policy.window_seconds)
        return response

    @app.middleware('http')
    async def protect_sensitive_responses(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['Referrer-Policy'] = 'no-referrer'
            response.headers['X-Frame-Options'] = 'DENY'
        return response

    # Canonical action routes are registered before the legacy expense router.
    # Blocking SQLAlchemy/filesystem work lives in normal def routes so FastAPI
    # executes it in its threadpool instead of blocking the event loop.
    app.include_router(request_actions.router, prefix='/api/expenses', tags=['Expenses'])
    app.include_router(revision_actions.router, prefix='/api/expenses', tags=['Expenses'])
    app.include_router(cancellation_actions.router, prefix='/api/expenses', tags=['Expenses'])
    app.include_router(closure_delegation.router, prefix='/api/expenses', tags=['Closure Delegation'])
    app.include_router(quotation_actions.router, prefix='/api/expenses', tags=['Expenses'])
    app.include_router(document_actions.router, prefix='/api/expenses', tags=['Documents'])
    app.include_router(financial_actions.router, prefix='/api/expenses', tags=['Expenses'])
    app.include_router(my_actions.router, prefix='/api/expenses', tags=['My Request Actions'])
    app.include_router(tracking.router, prefix='/api/expenses', tags=['Request Tracking'])
    app.include_router(dashboard.router, prefix='/api/expenses', tags=['Dashboard'])
    app.include_router(expenses.router, prefix='/api/expenses', tags=['Expenses (legacy compatibility)'])
    app.include_router(
        direct_expenses.router,
        prefix='/api/direct-expenses',
        tags=['Direct Expenses'],
    )
    app.include_router(organization_overview.router, prefix='/api/organization', tags=['Organization Overview'])
    app.include_router(approvals.router, prefix='/api/approvals', tags=['Approvals'])
    app.include_router(
        rules.router,
        prefix='/api/rules',
        tags=['Approval Rules'],
        dependencies=[Depends(require_permission('config:manage'))],
    )
    app.include_router(auth.router, prefix='/api/auth', tags=['Authentication'])
    # The legacy Organigrama screen still submits users.title. Register this
    # compatibility bridge first so PATCH /api/users/bulk updates canonical
    # UserPosition assignments and sends Cargo/permission notifications.
    app.include_router(
        legacy_position_notifications.router,
        prefix='/api/users',
        tags=['Users (canonical Cargo bridge)'],
    )
    app.include_router(
        users.router,
        prefix='/api/users',
        tags=['Users (legacy compatibility)'],
        dependencies=[Depends(require_permission('config:manage'))],
    )
    app.include_router(areas.router, prefix='/api/areas', tags=['Areas'])
    app.include_router(
        audit.router,
        prefix='/api/audit',
        tags=['Audit'],
        dependencies=[Depends(require_permission('config:manage'))],
    )
    app.include_router(iam_users.router, prefix='/api/iam/users', tags=['Access Management'])
    app.include_router(iam_group_assignments.router, prefix='/api/iam', tags=['Access Management'])
    app.include_router(iam_access_policy.router, prefix='/api/iam', tags=['Access Policy'])
    # Position endpoints remain only for the organizational chart. Authorization
    # ignores cargos and the policy router blocks new cargo-to-role grants.
    app.include_router(position_access.router, prefix='/api/iam', tags=['Organization Compatibility'])
    app.include_router(iam.router, prefix='/api/iam', tags=['Access Management'])

    @app.get('/api/health')
    def health():
        return {'status': 'ok'}

    return app


app = create_app()
