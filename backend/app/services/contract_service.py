import re
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.models.data_contract import DataContract
from backend.app.models.dataset import Dataset
from backend.app.schemas.contract import ContractCreate, ContractRules, ContractUpdate


class ContractError(Exception):
    """Raised for invalid or unavailable data contracts."""


def create_contract(
    db: Session, dataset_id: uuid.UUID, request: ContractCreate
) -> DataContract:
    _validate_rules(request.rules)
    try:
        dataset = db.scalar(select(Dataset).where(Dataset.id == dataset_id).with_for_update())
        if dataset is None:
            raise ContractError("Dataset not found.")
        version = int(
            db.scalar(
                select(func.coalesce(func.max(DataContract.version), 0)).where(
                    DataContract.dataset_id == dataset_id
                )
            )
            or 0
        ) + 1
        if request.active:
            _deactivate_all(db, dataset_id)
        contract = DataContract(
            dataset_id=dataset_id,
            version=version,
            name=request.name,
            description=request.description,
            rules=request.rules.model_dump(mode="json"),
            active=request.active,
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        return contract
    except ContractError:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise ContractError("Database failure while creating contract.") from exc


def update_contract_version(
    db: Session,
    dataset_id: uuid.UUID,
    contract_id: uuid.UUID,
    request: ContractUpdate,
) -> DataContract:
    current = get_contract(db, dataset_id, contract_id)
    if current is None:
        raise ContractError("Contract not found.")
    rules = ContractRules.model_validate(request.rules or current.rules)
    _validate_rules(rules)
    create_request = ContractCreate(
        name=request.name if request.name is not None else current.name,
        description=request.description if "description" in request.model_fields_set else current.description,
        rules=rules,
        active=request.active if request.active is not None else current.active,
    )
    new_contract = create_contract(db, dataset_id, create_request)
    new_contract.previous_version_id = current.id
    db.commit()
    db.refresh(new_contract)
    return new_contract


def list_contracts(db: Session, dataset_id: uuid.UUID) -> list[DataContract]:
    return list(
        db.scalars(
            select(DataContract)
            .where(DataContract.dataset_id == dataset_id)
            .order_by(DataContract.version.desc())
        ).all()
    )


def get_contract(
    db: Session, dataset_id: uuid.UUID, contract_id: uuid.UUID
) -> DataContract | None:
    return db.scalar(
        select(DataContract).where(
            DataContract.id == contract_id, DataContract.dataset_id == dataset_id
        )
    )


def get_active_contract(db: Session, dataset_id: uuid.UUID) -> DataContract | None:
    return db.scalar(
        select(DataContract).where(
            DataContract.dataset_id == dataset_id, DataContract.active.is_(True)
        )
    )


def set_contract_active(
    db: Session, dataset_id: uuid.UUID, contract_id: uuid.UUID, *, active: bool
) -> DataContract:
    try:
        db.scalar(select(Dataset).where(Dataset.id == dataset_id).with_for_update())
        contract = get_contract(db, dataset_id, contract_id)
        if contract is None:
            raise ContractError("Contract not found.")
        if active:
            _deactivate_all(db, dataset_id)
        contract.active = active
        db.commit()
        db.refresh(contract)
        return contract
    except ContractError:
        db.rollback()
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise ContractError("Database failure while updating contract status.") from exc


def _deactivate_all(db: Session, dataset_id: uuid.UUID) -> None:
    db.execute(
        update(DataContract)
        .where(DataContract.dataset_id == dataset_id, DataContract.active.is_(True))
        .values(active=False)
    )


def _validate_rules(rules: ContractRules) -> None:
    dataset = rules.dataset_rules
    if (
        dataset.minimum_row_count is not None
        and dataset.maximum_row_count is not None
        and dataset.minimum_row_count > dataset.maximum_row_count
    ):
        raise ContractError("minimum_row_count cannot exceed maximum_row_count.")
    for name, rule in rules.columns.items():
        if not name.strip():
            raise ContractError("Contract column names cannot be blank.")
        if (
            rule.minimum_length is not None
            and rule.maximum_length is not None
            and rule.minimum_length > rule.maximum_length
        ):
            raise ContractError(f"Invalid length bounds for column '{name}'.")
        if (
            rule.minimum_distinct_count is not None
            and rule.maximum_distinct_count is not None
            and rule.minimum_distinct_count > rule.maximum_distinct_count
        ):
            raise ContractError(f"Invalid distinct-count bounds for column '{name}'.")
        if rule.regex_pattern is not None:
            try:
                re.compile(rule.regex_pattern)
            except re.error as exc:
                raise ContractError(f"Invalid regex pattern for column '{name}'.") from exc
