/**
 * Thin wrapper around HA's WebSocket API for the HAIR backend.
 *
 * The HA frontend exposes a connection on the panel host element via
 * the `hass` property; we use `hass.connection.sendMessagePromise` for
 * one-shot commands and `hass.connection.subscribeMessage` for
 * streaming capture events.
 */
import type {
    ActionOption,
    AssignResult,
    CaptureEvent,
    CaptureProviderInfo,
    CaptureStartResponse,
    CommandTemplate,
    DeleteSignalResult,
    DeviceSummary,
    DeviceTypeId,
    IRCommand,
    IRDevice,
    IRTrigger,
    ReceiverInfo,
    SignalRemovedEvent,
    TestSignalResult,
    TriggerFiredEvent,
    UnknownDevice,
    UnknownDeviceSummary,
    UnknownSignalEvent,
} from "./types.js";

interface HaConnection {
    sendMessagePromise<T = unknown>(message: Record<string, unknown>): Promise<T>;
    subscribeMessage<T = unknown>(
        callback: (message: T) => void,
        message: Record<string, unknown>,
    ): Promise<() => Promise<void>>;
    subscribeEvents<T = unknown>(
        callback: (event: { event_type: string; data: T }) => void,
        eventType: string,
    ): Promise<() => Promise<void>>;
}

interface HassLike {
    connection: HaConnection;
}

export class HairApi {
    constructor(private readonly hass: HassLike) {}

    listDevices(): Promise<DeviceSummary[]> {
        return this.hass.connection.sendMessagePromise<DeviceSummary[]>({
            type: "hair/devices",
        });
    }

    getDevice(deviceId: string): Promise<IRDevice> {
        return this.hass.connection.sendMessagePromise<IRDevice>({
            type: "hair/device",
            device_id: deviceId,
        });
    }

    createDevice(payload: {
        name: string;
        device_type: DeviceTypeId;
        emitter_entity_ids: string[];
        manufacturer?: string | null;
        model?: string | null;
        capture_device_id?: string | null;
        capture_provider_type?: string;
    }): Promise<IRDevice> {
        return this.hass.connection.sendMessagePromise<IRDevice>({
            type: "hair/device/create",
            ...payload,
        });
    }

    updateDevice(
        deviceId: string,
        patch: Partial<{
            name: string;
            manufacturer: string | null;
            model: string | null;
            emitter_entity_ids: string[];
            device_type: string;
        }>,
    ): Promise<IRDevice> {
        return this.hass.connection.sendMessagePromise<IRDevice>({
            type: "hair/device/update",
            device_id: deviceId,
            ...patch,
        });
    }

    deleteDevice(deviceId: string): Promise<{ removed: boolean }> {
        return this.hass.connection.sendMessagePromise<{ removed: boolean }>({
            type: "hair/device/delete",
            device_id: deviceId,
        });
    }

    deleteCommand(deviceId: string, commandId: string): Promise<{ removed: boolean }> {
        return this.hass.connection.sendMessagePromise<{ removed: boolean }>({
            type: "hair/command/delete",
            device_id: deviceId,
            command_id: commandId,
        });
    }

    sendCommand(deviceId: string, commandId: string): Promise<{ sent: boolean }> {
        return this.hass.connection.sendMessagePromise<{ sent: boolean }>({
            type: "hair/command/send",
            device_id: deviceId,
            command_id: commandId,
        });
    }

    listTemplates(deviceType: DeviceTypeId): Promise<CommandTemplate[]> {
        return this.hass.connection.sendMessagePromise<CommandTemplate[]>({
            type: "hair/templates",
            device_type: deviceType,
        });
    }

    listCaptureProviders(): Promise<CaptureProviderInfo[]> {
        return this.hass.connection.sendMessagePromise<CaptureProviderInfo[]>({
            type: "hair/capture/providers",
        });
    }

    listReceivers(): Promise<ReceiverInfo[]> {
        return this.hass.connection.sendMessagePromise<ReceiverInfo[]>({
            type: "hair/receivers",
        });
    }

    /**
     * Start a capture session and stream events to ``onEvent``.
     * The returned promise resolves with the session id once the server
     * acknowledges; the unsubscribe function should be called when the
     * caller is done listening.
     */
    async startCapture(
        deviceId: string,
        timeout: number,
        onEvent: (event: CaptureEvent) => void,
    ): Promise<{ session: CaptureStartResponse; unsubscribe: () => Promise<void> }> {
        let session: CaptureStartResponse | null = null;

        const unsubscribe = await this.hass.connection.subscribeMessage<
            CaptureEvent | CaptureStartResponse
        >(
            (message) => {
                if ((message as CaptureEvent).type?.startsWith("capture_")) {
                    onEvent(message as CaptureEvent);
                } else if ((message as CaptureStartResponse).session_id) {
                    session = message as CaptureStartResponse;
                }
            },
            {
                type: "hair/capture/start",
                device_id: deviceId,
                timeout,
            },
        );

        // Allow microtask flush so the synchronous result message is
        // delivered before we resolve.
        await Promise.resolve();
        if (session === null) {
            throw new Error("Capture session did not start");
        }
        return { session, unsubscribe };
    }

    cancelCapture(sessionId: string): Promise<{ cancelled: boolean }> {
        return this.hass.connection.sendMessagePromise<{ cancelled: boolean }>({
            type: "hair/capture/cancel",
            session_id: sessionId,
        });
    }

    saveCapturedCommand(payload: {
        device_id: string;
        session_id: string;
        command_name: string;
        command_category?: string;
    }): Promise<IRCommand> {
        return this.hass.connection.sendMessagePromise<IRCommand>({
            type: "hair/capture/save",
            ...payload,
        });
    }

    // --- Action Mapping ---

    getActionOptions(deviceType: DeviceTypeId): Promise<ActionOption[]> {
        return this.hass.connection.sendMessagePromise<ActionOption[]>({
            type: "hair/device/action-options",
            device_type: deviceType,
        });
    }

    updateMapping(
        deviceId: string,
        commandName: string,
        actionKey: string | null,
    ): Promise<{ mapping: Record<string, string> }> {
        return this.hass.connection.sendMessagePromise<{ mapping: Record<string, string> }>({
            type: "hair/device/update-mapping",
            device_id: deviceId,
            command_name: commandName,
            action_key: actionKey,
        });
    }

    // --- Signal Monitor (Unknown Devices) ---

    getUnknownDevices(options?: {
        include_dismissed?: boolean;
        min_hits?: number;
    }): Promise<UnknownDeviceSummary[]> {
        return this.hass.connection.sendMessagePromise<UnknownDeviceSummary[]>({
            type: "hair/unknown/devices",
            ...options,
        });
    }

    getUnknownDevice(deviceId: string): Promise<UnknownDevice> {
        return this.hass.connection.sendMessagePromise<UnknownDevice>({
            type: "hair/unknown/device",
            device_id: deviceId,
        });
    }

    dismissUnknown(deviceId: string): Promise<{ dismissed: boolean }> {
        return this.hass.connection.sendMessagePromise<{ dismissed: boolean }>({
            type: "hair/unknown/dismiss",
            device_id: deviceId,
        });
    }

    undismissUnknown(deviceId: string): Promise<{ undismissed: boolean }> {
        return this.hass.connection.sendMessagePromise<{ undismissed: boolean }>({
            type: "hair/unknown/undismiss",
            device_id: deviceId,
        });
    }

    assignSignal(payload: {
        device_id: string;
        signal_fingerprint: string;
        hair_device_id: string;
        command_name: string;
        command_category?: string;
    }): Promise<AssignResult> {
        return this.hass.connection.sendMessagePromise<AssignResult>({
            type: "hair/unknown/assign",
            ...payload,
        });
    }

    assignToNewDevice(payload: {
        device_id: string;
        signal_fingerprint: string;
        device_name: string;
        device_type: string;
        emitter_entity_ids: string[];
        command_name: string;
        command_category?: string;
    }): Promise<AssignResult> {
        return this.hass.connection.sendMessagePromise<AssignResult>({
            type: "hair/unknown/assign-new-device",
            ...payload,
        });
    }

    deleteSignal(
        deviceId: string,
        signalFingerprint: string,
    ): Promise<DeleteSignalResult> {
        return this.hass.connection.sendMessagePromise<DeleteSignalResult>({
            type: "hair/unknown/signal/delete",
            device_id: deviceId,
            signal_fingerprint: signalFingerprint,
        });
    }

    testSignal(
        signalFingerprint: string,
        emitterEntityId?: string,
    ): Promise<TestSignalResult> {
        const msg: Record<string, unknown> = {
            type: "hair/unknown/test",
            signal_fingerprint: signalFingerprint,
        };
        if (emitterEntityId) {
            msg.emitter_entity_id = emitterEntityId;
        }
        return this.hass.connection.sendMessagePromise<TestSignalResult>(msg);
    }

    renameUnknown(
        deviceId: string,
        label: string,
    ): Promise<{ label: string | null }> {
        return this.hass.connection.sendMessagePromise<{ label: string | null }>({
            type: "hair/unknown/rename",
            device_id: deviceId,
            label,
        });
    }

    clearUnknowns(): Promise<{ cleared: boolean }> {
        return this.hass.connection.sendMessagePromise<{ cleared: boolean }>({
            type: "hair/unknown/clear",
        });
    }

    /**
     * Subscribe to live unknown-signal events via HA bus.
     * Returns an unsubscribe function.
     */
    async subscribeUnknownSignals(
        onEvent: (event: UnknownSignalEvent) => void,
    ): Promise<() => Promise<void>> {
        return this.hass.connection.subscribeEvents<UnknownSignalEvent>(
            (ev) => onEvent(ev.data),
            "hair_signal_detected",
        );
    }

    /**
     * Subscribe to signal-removed events (fired when signals are deleted
     * or assigned). Returns an unsubscribe function.
     */
    async subscribeSignalRemoved(
        onEvent: (event: SignalRemovedEvent) => void,
    ): Promise<() => Promise<void>> {
        return this.hass.connection.subscribeEvents<SignalRemovedEvent>(
            (ev) => onEvent(ev.data),
            "hair_signal_removed",
        );
    }

    // --- Triggers ---

    listTriggers(): Promise<IRTrigger[]> {
        return this.hass.connection.sendMessagePromise<IRTrigger[]>({
            type: "hair/triggers",
        });
    }

    createTrigger(payload: {
        name: string;
        signal_fingerprint?: string;
        protocol?: string | null;
        code?: string | null;
        min_hits?: number;
        source_device_id?: string | null;
        source_command_id?: string | null;
    }): Promise<IRTrigger> {
        return this.hass.connection.sendMessagePromise<IRTrigger>({
            type: "hair/trigger/create",
            ...payload,
        });
    }

    updateTrigger(
        triggerId: string,
        patch: Partial<{
            name: string;
            min_hits: number;
            enabled: boolean;
        }>,
    ): Promise<IRTrigger> {
        return this.hass.connection.sendMessagePromise<IRTrigger>({
            type: "hair/trigger/update",
            trigger_id: triggerId,
            ...patch,
        });
    }

    deleteTrigger(triggerId: string): Promise<{ removed: boolean }> {
        return this.hass.connection.sendMessagePromise<{ removed: boolean }>({
            type: "hair/trigger/delete",
            trigger_id: triggerId,
        });
    }

    /**
     * Subscribe to real-time trigger-fired events via WS subscription.
     * Returns an unsubscribe function.
     */
    async subscribeTriggerFired(
        onEvent: (event: TriggerFiredEvent) => void,
    ): Promise<() => Promise<void>> {
        return this.hass.connection.subscribeMessage<TriggerFiredEvent>(
            onEvent,
            { type: "hair/trigger/subscribe" },
        );
    }
}
