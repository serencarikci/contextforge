"""SQLAlchemy implementation of the RBAC repository.

Covers roles, permissions, and role assignments (organization-, project-, and
knowledge-space-scoped grants of a role to an organization membership).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import ColumnExpressionArgument, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from contextforge.modules.identity_access.domain.entities.rbac import (
    Permission,
    Role,
    RoleAssignment,
)
from contextforge.modules.identity_access.infrastructure.models.permission import PermissionModel
from contextforge.modules.identity_access.infrastructure.models.role import RoleModel
from contextforge.modules.identity_access.infrastructure.models.role_assignment import (
    RoleAssignmentModel,
)
from contextforge.modules.identity_access.infrastructure.models.role_permission import (
    RolePermissionModel,
)


class SqlAlchemyRbacRepository:
    """Persists roles, permissions, and role assignments using an explicit AsyncSession."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_roles(self, organization_id: UUID) -> list[Role]:
        statement = (
            select(RoleModel)
            .where(
                or_(
                    RoleModel.organization_id.is_(None),
                    RoleModel.organization_id == organization_id,
                )
            )
            .order_by(RoleModel.is_system.desc(), RoleModel.code.asc())
        )
        result = await self._session.execute(statement)
        return [self._role_to_entity(model) for model in result.scalars().all()]

    async def get_role(self, role_id: UUID) -> Role | None:
        statement = select(RoleModel).where(RoleModel.id == role_id)
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._role_to_entity(model)

    async def get_system_role_by_code(self, code: str) -> Role | None:
        statement = select(RoleModel).where(
            RoleModel.code == code,
            RoleModel.organization_id.is_(None),
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._role_to_entity(model)

    async def get_org_role_by_code(self, organization_id: UUID, code: str) -> Role | None:
        statement = select(RoleModel).where(
            RoleModel.organization_id == organization_id,
            RoleModel.code == code,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return None
        return self._role_to_entity(model)

    async def add_role(self, role: Role) -> Role:
        model = RoleModel(
            id=role.id,
            organization_id=role.organization_id,
            code=role.code,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            created_at=role.created_at,
            updated_at=role.updated_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._role_to_entity(model)

    async def update_role(self, role: Role) -> Role:
        statement = select(RoleModel).where(RoleModel.id == role.id)
        result = await self._session.execute(statement)
        model = result.scalar_one()

        model.name = role.name
        model.description = role.description
        model.updated_at = role.updated_at

        await self._session.flush()
        return self._role_to_entity(model)

    async def list_permissions(self) -> list[Permission]:
        statement = select(PermissionModel).order_by(PermissionModel.code.asc())
        result = await self._session.execute(statement)
        return [self._permission_to_entity(model) for model in result.scalars().all()]

    async def get_organization_scope_permission_codes(
        self, organization_id: UUID, membership_id: UUID
    ) -> set[str]:
        return await self._collect_permission_codes(
            organization_id,
            membership_id,
            RoleAssignmentModel.project_id.is_(None),
            RoleAssignmentModel.knowledge_space_id.is_(None),
        )

    async def get_project_scope_permission_codes(
        self, organization_id: UUID, membership_id: UUID, project_id: UUID
    ) -> set[str]:
        return await self._collect_permission_codes(
            organization_id,
            membership_id,
            RoleAssignmentModel.project_id == project_id,
        )

    async def get_knowledge_space_scope_permission_codes(
        self, organization_id: UUID, membership_id: UUID, knowledge_space_id: UUID
    ) -> set[str]:
        return await self._collect_permission_codes(
            organization_id,
            membership_id,
            RoleAssignmentModel.knowledge_space_id == knowledge_space_id,
        )

    async def _collect_permission_codes(
        self,
        organization_id: UUID,
        membership_id: UUID,
        *scope_conditions: ColumnExpressionArgument[bool],
    ) -> set[str]:
        statement = (
            select(PermissionModel.code)
            .select_from(RoleAssignmentModel)
            .join(RoleModel, RoleModel.id == RoleAssignmentModel.role_id)
            .join(RolePermissionModel, RolePermissionModel.role_id == RoleModel.id)
            .join(PermissionModel, PermissionModel.id == RolePermissionModel.permission_id)
            .where(
                RoleAssignmentModel.organization_id == organization_id,
                RoleAssignmentModel.membership_id == membership_id,
                *scope_conditions,
            )
        )
        result = await self._session.execute(statement)
        return set(result.scalars().all())

    async def list_accessible_project_ids(
        self, organization_id: UUID, membership_id: UUID
    ) -> set[UUID]:
        statement = select(RoleAssignmentModel.project_id).where(
            RoleAssignmentModel.organization_id == organization_id,
            RoleAssignmentModel.membership_id == membership_id,
            RoleAssignmentModel.project_id.is_not(None),
        )
        result = await self._session.execute(statement)
        return {project_id for project_id in result.scalars().all() if project_id is not None}

    async def list_accessible_knowledge_space_ids_from_roles(
        self, organization_id: UUID, membership_id: UUID
    ) -> set[UUID]:
        statement = select(RoleAssignmentModel.knowledge_space_id).where(
            RoleAssignmentModel.organization_id == organization_id,
            RoleAssignmentModel.membership_id == membership_id,
            RoleAssignmentModel.knowledge_space_id.is_not(None),
        )
        result = await self._session.execute(statement)
        return {ks_id for ks_id in result.scalars().all() if ks_id is not None}

    async def add_assignment(self, assignment: RoleAssignment) -> RoleAssignment:
        model = RoleAssignmentModel(
            id=assignment.id,
            organization_id=assignment.organization_id,
            membership_id=assignment.membership_id,
            role_id=assignment.role_id,
            project_id=assignment.project_id,
            knowledge_space_id=assignment.knowledge_space_id,
            created_at=assignment.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._assignment_to_entity(model)

    async def delete_assignment(self, organization_id: UUID, assignment_id: UUID) -> bool:
        statement = select(RoleAssignmentModel).where(
            RoleAssignmentModel.id == assignment_id,
            RoleAssignmentModel.organization_id == organization_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return False
        await self._session.delete(model)
        await self._session.flush()
        return True

    async def list_assignments(
        self, organization_id: UUID, *, limit: int, offset: int
    ) -> tuple[list[RoleAssignment], int]:
        count_statement = (
            select(func.count())
            .select_from(RoleAssignmentModel)
            .where(RoleAssignmentModel.organization_id == organization_id)
        )
        total = (await self._session.execute(count_statement)).scalar_one()

        statement = (
            select(RoleAssignmentModel)
            .where(RoleAssignmentModel.organization_id == organization_id)
            .order_by(RoleAssignmentModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [self._assignment_to_entity(model) for model in models], total

    async def assignment_exists(
        self,
        organization_id: UUID,
        membership_id: UUID,
        role_id: UUID,
        project_id: UUID | None,
        knowledge_space_id: UUID | None,
    ) -> bool:
        conditions = [
            RoleAssignmentModel.organization_id == organization_id,
            RoleAssignmentModel.membership_id == membership_id,
            RoleAssignmentModel.role_id == role_id,
            (
                RoleAssignmentModel.project_id == project_id
                if project_id is not None
                else RoleAssignmentModel.project_id.is_(None)
            ),
            (
                RoleAssignmentModel.knowledge_space_id == knowledge_space_id
                if knowledge_space_id is not None
                else RoleAssignmentModel.knowledge_space_id.is_(None)
            ),
        ]
        statement = select(func.count()).select_from(RoleAssignmentModel).where(and_(*conditions))
        result = await self._session.execute(statement)
        return result.scalar_one() > 0

    @staticmethod
    def _role_to_entity(model: RoleModel) -> Role:
        return Role(
            code=model.code,
            name=model.name,
            organization_id=model.organization_id,
            description=model.description,
            is_system=model.is_system,
            id=model.id,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    @staticmethod
    def _permission_to_entity(model: PermissionModel) -> Permission:
        return Permission(
            code=model.code,
            description=model.description,
            id=model.id,
            created_at=model.created_at,
        )

    @staticmethod
    def _assignment_to_entity(model: RoleAssignmentModel) -> RoleAssignment:
        return RoleAssignment(
            organization_id=model.organization_id,
            membership_id=model.membership_id,
            role_id=model.role_id,
            id=model.id,
            project_id=model.project_id,
            knowledge_space_id=model.knowledge_space_id,
            created_at=model.created_at,
        )
