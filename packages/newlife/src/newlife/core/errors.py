"""Typed failures of the four frozen contracts (port of the pressure-test
error taxonomy, byte-identical class set; see docs/design/proposal.md §5.2)."""


class ContractError(RuntimeError):
    """Base class for the frozen contract failure taxonomy."""


class ClaimValidationError(ContractError):
    pass


class SpecValidationError(ContractError):
    pass


class UnknownEffectKindError(SpecValidationError):
    pass


class ResolverRegistrationError(SpecValidationError):
    pass


class CommitAuthorityError(ContractError):
    pass


class PlaneAuthorityError(ContractError):
    pass


class StructuralOwnershipConflictError(ContractError):
    pass


class ReadOnlyStateError(ContractError):
    pass


class InterventionScopeError(ContractError):
    pass


class InvalidIntervalError(ContractError):
    pass


class DuplicateContributionError(ContractError):
    pass


class UnknownContributionError(ContractError):
    pass


class IncompleteContributionSetError(ContractError):
    pass


class AtomicBatchError(ContractError):
    pass


class StatePathError(ContractError):
    pass

