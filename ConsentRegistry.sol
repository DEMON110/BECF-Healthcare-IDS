// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title BECF Consent Registry
/// @notice Minimal, auditable consent-management contract for the BECF prototype.
/// @dev Stores consent metadata and emits immutable audit events. No patient data is stored on-chain.
contract ConsentRegistry {
    enum ConsentState { NONE, GRANTED, REVOKED, EXPIRED }

    struct Consent {
        ConsentState state;
        uint64 expiry;
        uint64 grantedAt;
    }

    mapping(address => mapping(address => mapping(bytes32 => Consent))) private consents;

    event ConsentGranted(address indexed patient, address indexed requestor, bytes32 indexed scope, uint256 expiry);
    event ConsentRevoked(address indexed patient, address indexed requestor, bytes32 indexed scope, uint256 timestamp);
    event ConsentExpired(address indexed patient, address indexed requestor, bytes32 indexed scope);
    event DataAccessed(address indexed requestor, address indexed patient, bytes32 indexed scope, uint256 timestamp);

    error ZeroAddress();
    error OnlyPatient();
    error InvalidExpiry();
    error ConsentNotGranted();
    error ConsentExpiredAlready();

    /// @notice Grant consent for a requestor and scope until a future expiry.
    function grantConsent(address requestor, bytes32 scope, uint64 expiry)
        external
        returns (ConsentState)
    {
        if (requestor == address(0)) revert ZeroAddress();
        if (msg.sender == address(0)) revert ZeroAddress();
        if (expiry <= block.timestamp) revert InvalidExpiry();

        consents[msg.sender][requestor][scope] = Consent({
            state: ConsentState.GRANTED,
            expiry: expiry,
            grantedAt: uint64(block.timestamp)
        });

        emit ConsentGranted(msg.sender, requestor, scope, expiry);
        return ConsentState.GRANTED;
    }

    /// @notice Revoke a previously granted consent. Only the patient can revoke it.
    function revokeConsent(address requestor, bytes32 scope)
        external
        returns (ConsentState)
    {
        if (requestor == address(0)) revert ZeroAddress();
        Consent storage c = consents[msg.sender][requestor][scope];
        c.state = ConsentState.REVOKED;
        emit ConsentRevoked(msg.sender, requestor, scope, block.timestamp);
        return ConsentState.REVOKED;
    }

    /// @notice Check whether the caller is currently authorized for a patient's scope.
    /// @dev This function does not return patient information; it only emits an audit event and returns authorization.
    function accessData(address patient, bytes32 scope)
        external
        returns (bool authorized)
    {
        if (patient == address(0)) revert ZeroAddress();
        Consent storage c = consents[patient][msg.sender][scope];
        if (c.state != ConsentState.GRANTED) revert ConsentNotGranted();
        if (block.timestamp >= c.expiry) {
            c.state = ConsentState.EXPIRED;
            emit ConsentExpired(patient, msg.sender, scope);
            revert ConsentExpiredAlready();
        }
        emit DataAccessed(msg.sender, patient, scope, block.timestamp);
        return true;
    }

    /// @notice Mark a consent as expired if its expiry time has passed.
    function checkExpiry(address patient, address requestor, bytes32 scope)
        external
        returns (ConsentState)
    {
        if (patient == address(0) || requestor == address(0)) revert ZeroAddress();
        Consent storage c = consents[patient][requestor][scope];
        if (c.state == ConsentState.GRANTED && block.timestamp >= c.expiry) {
            c.state = ConsentState.EXPIRED;
            emit ConsentExpired(patient, requestor, scope);
        }
        return c.state;
    }

    /// @notice Read consent metadata for audit/UI purposes.
    function getConsent(address patient, address requestor, bytes32 scope)
        external
        view
        returns (ConsentState state, uint64 expiry, uint64 grantedAt)
    {
        if (patient == address(0) || requestor == address(0)) revert ZeroAddress();
        Consent memory c = consents[patient][requestor][scope];
        return (c.state, c.expiry, c.grantedAt);
    }
}
