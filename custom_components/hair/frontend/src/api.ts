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
    CodeBrand,
    CommandTemplate,
    DeleteSignalResult,
    DeviceSummary,
    CombReport,
    CommandListenEvent,
    FittingListenEvent,
    FittingState,
    DeviceTypeId,
    DismissActivityEvent,
    IRCommand,
    IRDevice,
    IRTrigger,
    MatrixCells,
    PluckRunResult,
    PluckVendor,
    ProntoValidation,
    ReceiverInfo,
    SavePlan,
    SaveResult,
    SignalRemovedEvent,
    SignalSourceId,
    SignalUpdatedEvent,
    TestSignalResult,
    TriggerFiredEvent,
    UnknownDevice,
    UnknownDeviceSummary,
    UnknownSignal,
    UnknownSignalEvent,
    WigsList,
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
        promoted_from_unknown_id?: string | null;
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

    duplicateDevice(deviceId: string, newName: string): Promise<IRDevice> {
        return this.hass.connection.sendMessagePromise<IRDevice>({
            type: "hair/device/duplicate",
            device_id: deviceId,
            new_name: newName,
        });
    }

    deleteCommand(deviceId: string, commandId: string): Promise<{ removed: boolean }> {
        return this.hass.connection.sendMessagePromise<{ removed: boolean }>({
            type: "hair/command/delete",
            device_id: deviceId,
            command_id: commandId,
        });
    }

    setCommandTxForceRaw(
        deviceId: string,
        commandId: string,
        txForceRaw: boolean,
    ): Promise<{ tx_force_raw: boolean }> {
        return this.hass.connection.sendMessagePromise<{ tx_force_raw: boolean }>({
            type: "hair/command/set-tx-force-raw",
            device_id: deviceId,
            command_id: commandId,
            tx_force_raw: txForceRaw,
        });
    }

    /**
     * Persist a new command order for a device.
     *
     * ``commandIds`` must list every command currently on the device
     * exactly once -- the backend rejects mismatched sets with an
     * ``invalid_format`` error. Returns the canonical updated device so
     * the caller can reconcile any drift since the drag started.
     */
    reorderCommands(deviceId: string, commandIds: string[]): Promise<IRDevice> {
        return this.hass.connection.sendMessagePromise<IRDevice>({
            type: "hair/device/reorder-commands",
            device_id: deviceId,
            command_ids: commandIds,
        });
    }

    /**
     * Persist a new order for the HAIR device list. ``deviceIds`` must
     * list every device exactly once; the backend rejects a mismatched
     * set with ``invalid_format``.
     */
    reorderDevices(deviceIds: string[]): Promise<{ reordered: boolean }> {
        return this.hass.connection.sendMessagePromise<{ reordered: boolean }>({
            type: "hair/devices/reorder",
            device_ids: deviceIds,
        });
    }

    /** Transmit one command. ``heard`` reports whether the Mirror
     * caught this send's own echo within its wait -- the TEST button's
     * SENT . HEARD reading. A send nothing hears is still a send. */
    sendCommand(
        deviceId: string,
        commandId: string,
    ): Promise<{ sent: boolean; heard: boolean; receiver: string | null }> {
        return this.hass.connection.sendMessagePromise<{
            sent: boolean;
            heard: boolean;
            receiver: string | null;
        }>({
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

    getSnifferStatus(): Promise<{ has_receivers: boolean }> {
        return this.hass.connection.sendMessagePromise<{ has_receivers: boolean }>({
            type: "hair/sniffer/status",
        });
    }

    getCodeBrands(): Promise<CodeBrand[]> {
        return this.hass.connection.sendMessagePromise<CodeBrand[]>({
            type: "hair/codes/brands",
        });
    }

    importCodeRemote(
        codebookId: string,
        name?: string,
        includeMatrix?: boolean,
    ): Promise<{
        device: UnknownDevice;
        imported: number;
        skipped: number;
        // Duplicate-guard subset of skipped (2026-07-28): the matrix
        // clip's receipt names collapsed byte-identical cells so the
        // "up to {count}" promise and the created count reconcile.
        duplicates: number;
        merged?: boolean;
    }> {
        const msg: Record<string, unknown> = {
            type: "hair/codes/import-remote",
            codebook_id: codebookId,
        };
        if (name) msg.name = name;
        // The gated matrix clip (Cold Cuts second half): only ever sent
        // as an explicit true -- the backend default is closed.
        if (includeMatrix) msg.include_matrix = true;
        return this.hass.connection.sendMessagePromise(msg);
    }

    // --- Matrix cell browser (Cold Cuts second half, v0.8.8) ---

    matrixCells(deviceId: string): Promise<MatrixCells> {
        return this.hass.connection.sendMessagePromise<MatrixCells>({
            type: "hair/devices/matrix-cells",
            device_id: deviceId,
        });
    }

    /** Fire one exact cell, or a power code. Coordinates must be read
     * off matrixCells verbatim -- the backend resolves exactly, never
     * snaps. Resolves to the display-grammar name it sent as. */
    matrixSend(
        deviceId: string,
        state: {
            mode?: string;
            fan?: string | null;
            swing?: string | null;
            temp?: number | null;
            power?: "on" | "off";
        },
    ): Promise<{ sent: string }> {
        return this.hass.connection.sendMessagePromise<{ sent: string }>({
            type: "hair/devices/matrix-send",
            device_id: deviceId,
            ...state,
        });
    }

    /** Save one exact cell as a stored command (display-grammar name,
     * source "matrix", replace-by-name). Returns the full device. */
    matrixCommand(
        deviceId: string,
        state: {
            mode: string;
            fan?: string | null;
            swing?: string | null;
            temp?: number | null;
        },
    ): Promise<IRDevice> {
        return this.hass.connection.sendMessagePromise<IRDevice>({
            type: "hair/devices/matrix-command",
            device_id: deviceId,
            ...state,
        });
    }

    // --- Wigs (v0.7.0 Big Wig) ---

    wigsList(): Promise<WigsList> {
        return this.hass.connection.sendMessagePromise<WigsList>({
            type: "hair/wigs/list",
        });
    }

    wigsUpload(
        text: string,
        filename?: string,
    ): Promise<{
        success: boolean;
        filename?: string;
        filenames?: string[];
        files?: {
            filename: string;
            name: string;
            brand: string | null;
            duplicate_of: string | null;
            // Every closet wig holding an identical device (owner ask,
            // 2026-07-20): the receipt lists all of them, clickably.
            duplicates?: { filename: string; brand: string | null }[];
        }[];
        format?: string;
        skipped?: string[];
        errors?: string[];
    }> {
        const msg: Record<string, unknown> = {
            type: "hair/wigs/upload",
            text,
        };
        if (filename) msg.filename = filename;
        return this.hass.connection.sendMessagePromise(msg);
    }

    /** Comb one wig and refresh its receipt. Always re-combs rather than
     * serving the stored report: the receipt may predate a Replace. */
    /** Pin a catalog signal to raw replay, or unpin it (Highlights,
     * GH #78). The Sniffer / Clipper twin of the device command toggle. */
    setSignalTxForceRaw(
        deviceId: string,
        signalId: string,
        txForceRaw: boolean,
    ): Promise<{ tx_force_raw: boolean }> {
        return this.hass.connection.sendMessagePromise<{
            tx_force_raw: boolean;
        }>({
            type: "hair/unknown/signal/set-tx-force-raw",
            device_id: deviceId,
            signal_id: signalId,
            tx_force_raw: txForceRaw,
        });
    }

    wigsComb(filename: string): Promise<CombReport> {
        return this.hass.connection.sendMessagePromise<CombReport>({
            type: "hair/wigs/comb",
            filename,
        });
    }

    wigsDelete(filename: string): Promise<{ deleted: boolean }> {
        return this.hass.connection.sendMessagePromise<{ deleted: boolean }>({
            type: "hair/wigs/delete",
            filename,
        });
    }

    wigsGet(filename: string): Promise<{ filename: string; text: string }> {
        return this.hass.connection.sendMessagePromise<{
            filename: string;
            text: string;
        }>({ type: "hair/wigs/get", filename });
    }

    wigsUpdate(
        filename: string,
        patch: Partial<{
            name: string;
            brand: string;
            model: string;
            kind: string;
            notes: string;
            fcc_id: string;
            upc: string;
            asin: string;
            oem: string;
        }>,
    ): Promise<{ success: boolean; filename?: string; errors?: string[] }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/wigs/update",
            filename,
            ...patch,
        });
    }

    // --- Fitting (Perfect Fit) ---

    fittingState(filename: string): Promise<FittingState> {
        return this.hass.connection.sendMessagePromise<FittingState>({
            type: "hair/wigs/fitting/state",
            filename,
        });
    }

    fittingSend(
        filename: string,
        signalIndex: number,
        emitter: string,
        sendTimes?: number,
    ): Promise<{ success: boolean; heard: boolean; decoded: boolean }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/wigs/fitting/send",
            filename,
            signal_index: signalIndex,
            emitter,
            ...(sendTimes ? { send_times: sendTimes } : {}),
        });
    }

    fittingMark(
        filename: string,
        signalIndex: number,
        verdict: "worked" | "failed" | "untested",
    ): Promise<{
        success: boolean;
        confirmed: number;
        failed: number;
        total: number;
        perfect_ready: boolean;
    }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/wigs/fitting/mark",
            filename,
            signal_index: signalIndex,
            verdict,
        });
    }

    fittingFinish(
        filename: string,
        extras: Partial<{
            handle: string;
            github: string;
            note: string;
            kind: string;
        }>,
    ): Promise<{
        success: boolean;
        state: "perfect" | "partial";
        confirmed: number;
        failed: number;
        total: number;
        signed: boolean;
    }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/wigs/fitting/finish",
            filename,
            ...extras,
        });
    }

    /** Swap one fitting row's code (Smart Perm). The wig changes in
     * place and its identity rolls, so the caller refetches state. */
    fittingReplace(
        filename: string,
        signalIndex: number,
        pronto: string,
        source: "captured" | "pasted",
        // Highlights: the new code and its send decision are written in
        // ONE hash roll, so the row never exists in a state where the
        // bytes and the decision about them disagree.
        bypassProtocol = false,
    ): Promise<{
        success: boolean;
        content_hash: string;
        row_key: string;
        carried: number;
    }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/wigs/fitting/replace",
            filename,
            signal_index: signalIndex,
            pronto,
            source,
            bypass_protocol: bypassProtocol,
        });
    }

    /** Write a row's stated send count, or every row's (APPLY).
     *
     * The light path: send_count is out of the content hash, so this
     * rolls nothing and invalidates nobody's fitting. That is what
     * makes a bulk apply reasonable. */
    fittingSetSends(
        filename: string,
        signalIndex: number | null,
        sendCount: number,
    ): Promise<{ success: boolean; send_count: number; written: number }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/wigs/fitting/set_sends",
            filename,
            ...(signalIndex === null
                ? { all: true }
                : { signal_index: signalIndex }),
            send_count: sendCount,
        });
    }

    /** Hold a tuned ditto in the session so TEST transmits it.
     *
     * Nothing reaches the wig: a tuned value cannot enter the file
     * without a WORKED against it. Pass null to clear. */
    fittingStageDitto(
        filename: string,
        signalIndex: number,
        dittoCount: number | null,
    ): Promise<{ success: boolean; staged: number | null }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/wigs/fitting/stage_ditto",
            filename,
            signal_index: signalIndex,
            ditto_count: dittoCount,
        });
    }

    /** Commit a tuned ditto into the wig. Rolls the hash exactly as a
     * replace does, so the caller refetches state afterward. */
    fittingTune(
        filename: string,
        signalIndex: number,
        dittoCount: number,
    ): Promise<{
        success: boolean;
        content_hash: string;
        row_key: string;
        ditto_count: number;
        carried: number;
    }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/wigs/fitting/tune",
            filename,
            signal_index: signalIndex,
            ditto_count: dittoCount,
        });
    }

    /** Put one row back to the code the wig came with. Rolls the hash
     * back, so the caller refetches state exactly as after a replace. */
    fittingRevert(
        filename: string,
        signalIndex: number,
    ): Promise<{
        success: boolean;
        content_hash: string;
        row_key: string;
        carried: number;
    }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/wigs/fitting/revert",
            filename,
            signal_index: signalIndex,
        });
    }

    /** Arm the Sniffer for one capture into the Replace box. Emits a
     * single fitting_capture or fitting_listen_timeout; call the
     * returned unsubscribe on cancel or when the dialog closes. */
    async fittingListen(
        onEvent: (event: FittingListenEvent) => void,
    ): Promise<() => Promise<void>> {
        return this.hass.connection.subscribeMessage<FittingListenEvent>(
            onEvent,
            { type: "hair/wigs/fitting/listen" },
        );
    }

    /** What SAVE TO CLOSET is about to do, for the dialog to draw:
     * CREATE or UPDATE, the rows, what matched, what to prefill. A
     * photograph, not a session -- nothing is held between this and the
     * save that follows. */
    wigsSavePlan(deviceId: string): Promise<SavePlan> {
        return this.hass.connection.sendMessagePromise<SavePlan>({
            type: "hair/wigs/save_plan",
            device_id: deviceId,
        });
    }

    /** Save a device to the closet. ``mode`` is the person's answer,
     * not an inference: the dialog showed them which verb it offered,
     * so sending it back means a save cannot silently become the other
     * one because a file appeared or vanished mid-dialog. */
    wigsSave(payload: {
        device_id: string;
        mode: "create" | "update";
        name?: string;
        brand?: string;
        model?: string;
        notes?: string;
        kind?: string;
        fcc_id?: string;
        upc?: string;
        asin?: string;
        oem?: string;
        attest?: {
            claims: { digest: string; verdict: string }[];
            handle?: string;
            github?: string;
            note?: string;
            renames?: {
                digest: string;
                alias_at_claim: string;
                alias: string;
            }[];
            cells_hash?: string;
        };
    }): Promise<SaveResult> {
        return this.hass.connection.sendMessagePromise<SaveResult>({
            type: "hair/wigs/save",
            ...payload,
        });
    }

    /** Arm the Sniffer for one capture into the command editor's Pronto
     * box. Emits a single command_capture or command_listen_timeout;
     * call the returned unsubscribe on cancel or when the dialog
     * closes. */
    async commandListen(
        onEvent: (event: CommandListenEvent) => void,
    ): Promise<() => Promise<void>> {
        return this.hass.connection.subscribeMessage<CommandListenEvent>(
            onEvent,
            { type: "hair/command/listen" },
        );
    }

    fittingDiscard(filename: string): Promise<{ success: boolean }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/wigs/fitting/discard",
            filename,
        });
    }

    wigMakeDevice(
        source: { filename: string } | { codebookId: string },
        name: string,
        deviceType: DeviceTypeId,
        emitterEntityIds: string[],
    ): Promise<IRDevice & { copied: number; skipped: number }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/wigs/make-device",
            ...("filename" in source
                ? { filename: source.filename }
                : { codebook_id: source.codebookId }),
            name,
            device_type: deviceType,
            emitter_entity_ids: emitterEntityIds,
        });
    }

    wigSnapshot(
        codebookId: string,
    ): Promise<{ filename: string; name: string; existed: boolean }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/wigs/snapshot",
            codebook_id: codebookId,
        });
    }

    wigRender(
        codebookId: string,
    ): Promise<{ text: string; name: string; filename: string }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/wigs/render",
            codebook_id: codebookId,
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
        source?: SignalSourceId;
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
        signal_id: string;
        hair_device_id: string;
        command_name: string;
        command_category?: string;
        send_count?: number;
        repeat_count?: number;
    }): Promise<AssignResult> {
        return this.hass.connection.sendMessagePromise<AssignResult>({
            type: "hair/unknown/assign",
            ...payload,
        });
    }

    assignToNewDevice(payload: {
        device_id: string;
        signal_id: string;
        device_name: string;
        device_type: string;
        emitter_entity_ids: string[];
        command_name: string;
        command_category?: string;
        send_count?: number;
        repeat_count?: number;
    }): Promise<AssignResult> {
        return this.hass.connection.sendMessagePromise<AssignResult>({
            type: "hair/unknown/assign-new-device",
            ...payload,
        });
    }

    deleteSignal(
        deviceId: string,
        signalId: string,
    ): Promise<DeleteSignalResult> {
        return this.hass.connection.sendMessagePromise<DeleteSignalResult>({
            type: "hair/unknown/signal/delete",
            device_id: deviceId,
            signal_id: signalId,
        });
    }

    testSignal(
        signalId: string,
        emitterEntityId?: string,
    ): Promise<TestSignalResult> {
        const msg: Record<string, unknown> = {
            type: "hair/unknown/test",
            signal_id: signalId,
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

    clearUnknowns(source?: SignalSourceId): Promise<{ cleared: boolean }> {
        return this.hass.connection.sendMessagePromise<{ cleared: boolean }>({
            type: "hair/unknown/clear",
            ...(source ? { source } : {}),
        });
    }

    setSignalAlias(
        deviceId: string,
        signalId: string,
        alias: string,
    ): Promise<{ alias: string }> {
        return this.hass.connection.sendMessagePromise<{ alias: string }>({
            type: "hair/unknown/signal/set-alias",
            device_id: deviceId,
            signal_id: signalId,
            alias,
        });
    }

    /**
     * Persist a new order for one tab's remotes (Sniffer or Clipper).
     * ``deviceIds`` must be exactly the devices of that ``source``; the
     * backend rejects a mismatched set with ``invalid_format``.
     */
    reorderUnknownDevices(
        source: SignalSourceId,
        deviceIds: string[],
    ): Promise<{ reordered: boolean }> {
        return this.hass.connection.sendMessagePromise<{ reordered: boolean }>({
            type: "hair/unknown/reorder",
            source,
            device_ids: deviceIds,
        });
    }

    /**
     * Persist a new order for the signals within one remote. ``signalIds``
     * must list every signal on the remote exactly once; the backend rejects
     * a mismatched set with ``invalid_format``.
     */
    reorderUnknownSignals(
        deviceId: string,
        signalIds: string[],
    ): Promise<{ reordered: boolean }> {
        return this.hass.connection.sendMessagePromise<{ reordered: boolean }>({
            type: "hair/unknown/signal/reorder",
            device_id: deviceId,
            signal_ids: signalIds,
        });
    }

    // --- Clips (manual remotes / signals) ---

    createRemote(name: string): Promise<UnknownDevice> {
        return this.hass.connection.sendMessagePromise<UnknownDevice>({
            type: "hair/clip/create-remote",
            name,
        });
    }

    createSignal(payload: {
        device_id: string;
        pronto: string;
        alias?: string;
        send_count?: number;
        repeat_count?: number;
    }): Promise<{ signal: UnknownSignal }> {
        return this.hass.connection.sendMessagePromise<{ signal: UnknownSignal }>({
            type: "hair/clip/create-signal",
            ...payload,
        });
    }

    editSignalPronto(payload: {
        device_id: string;
        signal_id: string;
        pronto: string;
        alias?: string | null;
        send_count?: number;
        repeat_count?: number;
    }): Promise<{
        signal: UnknownSignal;
        triggers: { rewired: string[]; skipped: string[] };
    }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/unknown/signal/edit-pronto",
            ...payload,
        });
    }

    validatePronto(pronto: string): Promise<ProntoValidation> {
        return this.hass.connection.sendMessagePromise<ProntoValidation>({
            type: "hair/clip/validate-pronto",
            pronto,
        });
    }

    snapPreview(payload: {
        pronto: string;
        target_frequency: number;
    }): Promise<{ pronto: string; frequency_khz: number }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/unknown/signal/snap-preview",
            ...payload,
        });
    }

    updateCommand(payload: {
        device_id: string;
        command_id: string;
        name?: string;
        pronto?: string;
        send_count?: number;
        repeat_count?: number;
    }): Promise<{
        command: IRCommand;
        triggers: { rewired: string[]; skipped: string[] };
        mappings_updated: number;
    }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/command/update",
            ...payload,
        });
    }

    deleteRemote(deviceId: string): Promise<{ deleted: boolean }> {
        return this.hass.connection.sendMessagePromise<{ deleted: boolean }>({
            type: "hair/clip/delete-remote",
            device_id: deviceId,
        });
    }

    deleteSniffedRemote(deviceId: string): Promise<{ deleted: boolean }> {
        return this.hass.connection.sendMessagePromise<{ deleted: boolean }>({
            type: "hair/unknown/delete-remote",
            device_id: deviceId,
        });
    }

    // --- Plucker (vendor code import) ---

    listPluckVendors(): Promise<{ vendors: PluckVendor[] }> {
        return this.hass.connection.sendMessagePromise<{ vendors: PluckVendor[] }>({
            type: "hair/pluck/list-vendors",
        });
    }

    runPluck(payload: {
        integration: string;
        vendor_entity_id: string;
        appliance: string;
        command_name: string;
    }): Promise<PluckRunResult> {
        return this.hass.connection.sendMessagePromise<PluckRunResult>({
            type: "hair/pluck/run",
            ...payload,
        });
    }

    createPluckedBlaster(payload: {
        vendor_entity_id: string;
        appliance: string;
        name: string;
    }): Promise<UnknownDevice> {
        return this.hass.connection.sendMessagePromise<UnknownDevice>({
            type: "hair/pluck/create-blaster",
            ...payload,
        });
    }

    createPluckedSignal(payload: {
        device_id: string;
        pronto: string;
        command_name: string;
        alias?: string;
    }): Promise<UnknownSignal> {
        return this.hass.connection.sendMessagePromise<UnknownSignal>({
            type: "hair/pluck/create-signal",
            ...payload,
        });
    }

    deletePluckedBlaster(deviceId: string): Promise<{ deleted: boolean }> {
        return this.hass.connection.sendMessagePromise<{ deleted: boolean }>({
            type: "hair/pluck/delete-blaster",
            device_id: deviceId,
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

    /**
     * Subscribe to signal-updated events (fired when a signal's assignment
     * set changes: an assign, or a device command referencing it is added or
     * removed). Backed by the ``hair_signal_updated`` HA bus event. The
     * Sniffer/Clipper/Plucker wire this to refresh the green Assign badge and
     * yellow trigger dot live across browser tabs. Returns an unsubscribe fn.
     */
    async subscribeSignalUpdated(
        onEvent: (event: SignalUpdatedEvent) => void,
    ): Promise<() => Promise<void>> {
        return this.hass.connection.subscribeEvents<SignalUpdatedEvent>(
            (ev) => onEvent(ev.data),
            "hair_signal_updated",
        );
    }

    /**
     * Subscribe to dismiss-activity events. Fires (rate-limited) when a
     * signal arrives from a remote whose device fingerprint is in the
     * dismiss set. Backed by the ``hair_dismiss_activity`` HA bus event
     * which signal_monitor emits at Step 4 before dropping the signal.
     *
     * The Sniffer wires this to its "Show Dismissed" button glow + dot
     * indicator. The signal itself is NOT delivered through this channel
     * (and intentionally never reaches storage either) -- only the
     * device_fingerprint comes through, so consumers can tell which
     * dismissed remote is still firing without re-exposing the signal.
     */
    async subscribeDismissActivity(
        onEvent: (event: DismissActivityEvent) => void,
    ): Promise<() => Promise<void>> {
        return this.hass.connection.subscribeEvents<DismissActivityEvent>(
            (ev) => onEvent(ev.data),
            "hair_dismiss_activity",
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
        receiver_entity_ids?: string[];
        byte_hash?: string | null;
        decoded_fingerprint?: string | null;
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
            receiver_entity_ids: string[];
            byte_hash: string | null;
            decoded_fingerprint: string | null;
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
