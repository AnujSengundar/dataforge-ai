import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.schemas.contract import ContractCreate, ContractResponse, ContractUpdate
from backend.app.services.contract_service import (
    ContractError,
    create_contract,
    get_active_contract,
    get_contract,
    list_contracts,
    set_contract_active,
    update_contract_version,
)


router = APIRouter(prefix="/datasets/{dataset_id}/contracts", tags=["contracts"])


def _handle(error: ContractError) -> HTTPException:
    code = 404 if "not found" in str(error).lower() else 400
    return HTTPException(status_code=code, detail=str(error))


@router.post("", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
def create(
    dataset_id: uuid.UUID, request: ContractCreate, db: Session = Depends(get_db)
) -> ContractResponse:
    try:
        return ContractResponse.model_validate(create_contract(db, dataset_id, request))
    except ContractError as exc:
        raise _handle(exc) from exc


@router.get("", response_model=list[ContractResponse])
def list_all(dataset_id: uuid.UUID, db: Session = Depends(get_db)) -> list[ContractResponse]:
    return [ContractResponse.model_validate(item) for item in list_contracts(db, dataset_id)]


@router.get("/active", response_model=ContractResponse)
def active(dataset_id: uuid.UUID, db: Session = Depends(get_db)) -> ContractResponse:
    contract = get_active_contract(db, dataset_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Active contract not found.")
    return ContractResponse.model_validate(contract)


@router.get("/{contract_id}", response_model=ContractResponse)
def get_one(
    dataset_id: uuid.UUID, contract_id: uuid.UUID, db: Session = Depends(get_db)
) -> ContractResponse:
    contract = get_contract(db, dataset_id, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found.")
    return ContractResponse.model_validate(contract)


@router.put("/{contract_id}", response_model=ContractResponse)
def update(
    dataset_id: uuid.UUID,
    contract_id: uuid.UUID,
    request: ContractUpdate,
    db: Session = Depends(get_db),
) -> ContractResponse:
    try:
        return ContractResponse.model_validate(
            update_contract_version(db, dataset_id, contract_id, request)
        )
    except ContractError as exc:
        raise _handle(exc) from exc


@router.post("/{contract_id}/activate", response_model=ContractResponse)
def activate(
    dataset_id: uuid.UUID, contract_id: uuid.UUID, db: Session = Depends(get_db)
) -> ContractResponse:
    try:
        return ContractResponse.model_validate(
            set_contract_active(db, dataset_id, contract_id, active=True)
        )
    except ContractError as exc:
        raise _handle(exc) from exc


@router.post("/{contract_id}/deactivate", response_model=ContractResponse)
def deactivate(
    dataset_id: uuid.UUID, contract_id: uuid.UUID, db: Session = Depends(get_db)
) -> ContractResponse:
    try:
        return ContractResponse.model_validate(
            set_contract_active(db, dataset_id, contract_id, active=False)
        )
    except ContractError as exc:
        raise _handle(exc) from exc
