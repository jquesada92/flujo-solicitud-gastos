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
    document_actions,
    expenses,
    financial_actions,
    iam,
    iam_users,
    my_actions,
    position_access,
    quotation_actions,
    request_actions,
    revision_actions,
    rules,
    tracking,
    users,
)
from app.core.config import get_settings
from app.core.rate_limit import authenticated_subject, consume_user_request, policy_for_request
from app.core.security import require_permission


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
            subject = authenticated_subject(request.headers.get('authorization'))
            if subject:
                policy = policy_for_request(request.method, request.url.path)
                allowed, remaining, retry_after = consume_user_request(subject, policy)
                if not allowed:
                    return JSONResponse(
                        status_code=429,
                        content={'detail': f'Máximo {policy.limit} acciones de tipo {policy.name} por minuto'},
                        headers={'Retry-After': str(retry_after)},
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
    app.include_router(expenses.router, prefix='/api/expenses', tags=['Expenses (legacy compatibility)'])
    app.include_router(approvals.router, prefix='/api/approvals', tags=['Approvals'])
    app.include_router(
        rules.router,
        prefix='/api/rules',
        tags=['Approval Rules'],
        dependencies=[Depends(require_permission('config:manage'))],
    )
    app.include_router(auth.router, prefix='/api/auth', tags=['Authentication'])
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
    # Position access must precede the generic IAM router because it enriches
    # GET /positions with inherited role ids while legacy CRUD remains behind it.
    app.include_router(position_access.router, prefix='/api/iam', tags=['Access Management'])
    app.include_router(iam.router, prefix='/api/iam', tags=['Access Management'])

    @app.get('/api/health')
    def health():
        return {'status': 'ok'}

    return app


app = create_app()
