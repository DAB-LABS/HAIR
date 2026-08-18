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
    ClaimsLedger,
    CombReport,
    CommandListenEvent,
    DeviceTypeId,
    DismissActivityEvent,
    IRCommand,
    IRDevice,
    IRTrigger,
    MatrixCellDetail,
    MatrixCells,
    PluckRunResult,
    PluckVendor,
    ProntoValidation,
    ReceiverInfo,
    ReverseSupersessionBlock,
    SavePlan,
    SaveResult,
    SupersedeResult,
    SupersessionBlock,
    SignalRemovedEvent,
    SignalSourceId,
    SignalUpdatedEvent,
    TestSignalResult,
    TriggerDrawerInfo,
    TriggerRemoteInfo,
    TriggerFiredEvent,
    UnknownDevice,
    UnknownDeviceSummary,
    UnknownSignal,
    UnknownSignalEvent,
    WigsList,
    WigSignalIdentity,
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
            // Device Settings (0.9.8): power-sensor-based state
            // correction. Sending power_sensor_entity_id: null clears
            // it, which the backend also forces both thresholds to
            // null for (thresholds without a sensor are meaningless).
            power_sensor_entity_id: string | null;
            power_off_below_w: number | null;
            power_on_above_w: number | null;
            // Climate room sensors (climate-sensors.md), riding 0.9.8:
            // independent of each other and of the power fields above
            // -- either clears on its own with a null.
            temperature_sensor_entity_id: string | null;
            humidity_sensor_entity_id: string | null;
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

    /** The same lattice, read off a Remote instead of a Device
     * (signpost 4, Track M). Byte-identical payload -- the card is one
     * component in two moods -- with no send or command sibling,
     * because nothing transmits from a Remote. */
    remoteMatrixCells(remoteId: string): Promise<MatrixCells> {
        return this.hass.connection.sendMessagePromise<MatrixCells>({
            type: "hair/trigger-remote/matrix-cells",
            remote_id: remoteId,
        });
    }

    /** ONE cell's code, display name and identity, by the coordinates
     * remoteMatrixCells already handed over (signpost 4, Track M).
     * Read-only: this is what pre-fills the trigger dialog through each
     * of the three doors, and asking neither stores nor transmits
     * anything. Coordinates go over verbatim -- the backend resolves
     * exactly and never snaps -- and ``power`` is EXCLUSIVE with the
     * cell dimensions rather than winning over them, so a trigger about
     * to be minted can never quietly become a different one than the
     * card previewed. */
    remoteMatrixCell(
        remoteId: string,
        pick: {
            mode?: string | null;
            fan?: string | null;
            swing?: string | null;
            temp?: number | null;
            power?: "on" | "off" | null;
        },
    ): Promise<MatrixCellDetail> {
        const msg: Record<string, unknown> = {
            type: "hair/trigger-remote/matrix-cell",
            remote_id: remoteId,
        };
        if (pick.power) {
            msg.power = pick.power;
        } else {
            if (pick.mode != null) msg.mode = pick.mode;
            if (pick.fan != null) msg.fan = pick.fan;
            if (pick.swing != null) msg.swing = pick.swing;
            if (pick.temp != null) msg.temp = pick.temp;
        }
        return this.hass.connection.sendMessagePromise<MatrixCellDetail>(msg);
    }

    /** Fire one exact cell, or a power code. Coordinates must be read
     * off matrixCells verbatim -- the backend resolves exactly, never
     * snaps. Resolves to the display-grammar name it sent as, plus
     * the same SENT . HEARD reading sendCommand reports -- a cell
     * send rides the identical Mirror echo hook (Second Fitting v3
     * punch list item 14). */
    matrixSend(
        deviceId: string,
        state: {
            mode?: string;
            fan?: string | null;
            swing?: string | null;
            temp?: number | null;
            power?: "on" | "off";
        },
    ): Promise<{ sent: string; heard: boolean; receiver: string | null }> {
        return this.hass.connection.sendMessagePromise<{
            sent: string;
            heard: boolean;
            receiver: string | null;
        }>({
            type: "hair/devices/matrix-send",
            device_id: deviceId,
            ...state,
        });
    }

    /** Save one exact cell, or a power code, as a stored command
     * (display-grammar name, source "matrix", replace-by-name).
     * Exactly one of mode or power is required -- mirrors
     * matrixSend's own power-wins contract (matrix-power-row.md item
     * 2). Returns the full device. */
    matrixCommand(
        deviceId: string,
        state: {
            mode?: string;
            fan?: string | null;
            swing?: string | null;
            temp?: number | null;
            power?: "on" | "off";
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
        // Set on the resend that follows an owner Import Anyway, so the
        // reverse-supersession check below does not fire twice on the
        // same text (v0.9.7 Second Fitting, amendment v2 section 3).
        confirmed?: boolean,
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
            // Pre-claims fittings set aside on import (they cannot
            // become per-row claims); the receipt announces the count.
            dropped_fittings?: number;
        }[];
        format?: string;
        skipped?: string[];
        errors?: string[];
        // The replace-flow invitation, when the arrival names an ancestor
        // still in this closet (v0.9.7 Second Fitting).
        supersession?: SupersessionBlock;
        // The arrival names an id a newer LOCAL wig already lists as
        // superseded -- nothing files until the owner says Import
        // Anyway (v0.9.7 Second Fitting, amendment v2 section 3).
        reverse_supersession?: ReverseSupersessionBlock;
    }> {
        const msg: Record<string, unknown> = {
            type: "hair/wigs/upload",
            text,
        };
        if (filename) msg.filename = filename;
        if (confirmed) msg.confirmed = true;
        return this.hass.connection.sendMessagePromise(msg);
    }

    /** Perform the replace a superseding Wig invites: delete the old
     * file, repoint its devices, top up the chosen ones (v0.9.7). The
     * server re-verifies the pair, so a stale confirm refuses cleanly. */
    wigsSupersede(
        newFilename: string,
        oldFilename: string,
        relink: boolean,
        topupDeviceIds: string[],
    ): Promise<SupersedeResult> {
        return this.hass.connection.sendMessagePromise<SupersedeResult>({
            type: "hair/wigs/supersede",
            new_filename: newFilename,
            old_filename: oldFilename,
            relink,
            topup_device_ids: topupDeviceIds,
        });
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

    wigsGet(filename: string): Promise<{
        filename: string;
        text: string;
        download_filename: string;
    }> {
        return this.hass.connection.sendMessagePromise<{
            filename: string;
            text: string;
            download_filename: string;
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

    // --- Attestation (read side) ---

    /** The ledger: who attested what about this wig, in full detail.
     *
     * A pure read, and the only claims command there is. Attesting
     * happens through wigsSave, on the device that was tested; there
     * is nothing here to write with. */
    wigsClaims(filename: string): Promise<ClaimsLedger> {
        return this.hass.connection.sendMessagePromise<ClaimsLedger>({
            type: "hair/wigs/claims",
            filename,
        });
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

    /** Save a device to the closet. The verb is derived server-side
     * (Second Fitting amendment v2) from the device's own state at
     * save time for every route but one: Save As New sends
     * `mode: "create"` (v3 punch list item 2) to say the route itself
     * was the caller's choice, forcing a mint even over matching
     * content -- every other field here is still read fresh from the
     * device, never taken on the caller's word. */
    wigsSave(payload: {
        device_id: string;
        /** Second Fitting v3 punch list item 2: set only by the Save
         * As New dialog. Forces a mint regardless of what the fresh
         * server-side derivation would otherwise pick, and drops any
         * `replace` riding in the same payload -- Save As New never
         * touches the existing wig. */
        mode?: "create";
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
        };
        /** MATRIX UPDATE: send the repaired lattice upstream. */
        propose_lattice?: boolean;
        /** Second Fitting v3: the Update Closet Wig dialog's own
         * intent, set when its plan already says the device diverged.
         * The server re-derives the verb fresh and refuses a stale
         * one rather than acting on this alone. */
        replace?: boolean;
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

    /**
     * "Make a Device" mirror-door mint (signpost 3, Track 3.5, owner-
     * directed 2026-08-15): wigMakeDevice's twin, sourced from a live
     * Remote's own triggers instead of a closet wig
     * (hair/trigger-remote/make-device). No matrix concept on a
     * Remote's triggers, so device_type is a free pick, same as the
     * Manual add-device tab.
     */
    remoteMakeDevice(
        remoteId: string,
        name: string,
        deviceType: DeviceTypeId,
        emitterEntityIds: string[],
    ): Promise<IRDevice & { copied: number }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/trigger-remote/make-device",
            remote_id: remoteId,
            name,
            device_type: deviceType,
            emitter_entity_ids: emitterEntityIds,
        });
    }

    /**
     * Signpost 3, Track 2 item 2 / Track 3 item 1: USE as a Remote,
     * Closet door -- mints a named Remote straight from a wig (EITHER
     * a closet filename or a library codebook_id, same shape
     * wigMakeDevice uses), seeding one trigger per discrete signal in
     * one backend call (hair/wigs/make-remote). Mirrors wigMakeDevice
     * exactly except there is no device_type/emitter concept on the
     * remote side.
     */
    wigMakeRemote(
        source: { filename: string } | { codebookId: string },
        name: string,
        receiverScope: string[],
    ): Promise<TriggerRemoteInfo> {
        return this.hass.connection.sendMessagePromise<TriggerRemoteInfo>({
            type: "hair/wigs/make-remote",
            ...("filename" in source
                ? { filename: source.filename }
                : { codebook_id: source.codebookId }),
            name,
            receiver_scope: receiverScope,
        });
    }

    /**
     * "Make a Remote" mirror-door mint (signpost 3, Track 3.5, owner-
     * directed 2026-08-15): wigMakeRemote's twin, sourced from a live
     * Device's own commands instead of a closet wig
     * (hair/device/make-remote). Matrix-cell porthole rows are
     * excluded server-side, same discrete-press subset the device
     * picker already applies -- nothing for the caller to filter.
     */
    deviceMakeRemote(
        deviceId: string,
        name: string,
        receiverScope: string[],
    ): Promise<TriggerRemoteInfo> {
        return this.hass.connection.sendMessagePromise<TriggerRemoteInfo>({
            type: "hair/device/make-remote",
            device_id: deviceId,
            name,
            receiver_scope: receiverScope,
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

    /** Star or unstar a command (climate-presets-star.md).
     *
     * A starred command becomes a Home Assistant preset on the
     * device's climate entity, named exactly what the command is
     * named. Returns the resulting list so the row repaints without a
     * second round trip. Separate from updateMapping on purpose: a
     * command can be both mapped and starred, which one mapping key
     * per command could never express.
     */
    starCommand(
        deviceId: string,
        commandName: string,
        starred: boolean,
    ): Promise<{ starred: string[] }> {
        return this.hass.connection.sendMessagePromise<{ starred: string[] }>({
            type: "hair/device/star",
            device_id: deviceId,
            command_name: commandName,
            starred,
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
        // Add Popups signpost 2, Track 3. Both optional/absent by
        // default -- the drawer's own + Add Trigger dialog never sends
        // either and stays drawer-owned/origin-less, unaffected.
        trigger_remote_id?: string | null;
        origin?: string | null;
    }): Promise<IRTrigger> {
        return this.hass.connection.sendMessagePromise<IRTrigger>({
            type: "hair/trigger/create",
            ...payload,
        });
    }

    /**
     * Add Popups signpost 2, Track 3: create a named trigger remote.
     * Manual tab calls this alone (0 triggers seeded); Closet/Device
     * tabs call it first, then loop createTrigger() with
     * trigger_remote_id set to the result's id (wigSignals() /
     * getDevice() supply what to loop over).
     */
    createTriggerRemote(payload: {
        name: string;
        receiver_scope?: string[];
        origin?: string | null;
        // Signpost 3, Track 2 item 2 / Track 3 item 1: set when this
        // remote is minted from a Sniffer/Clipper/Plucker catalog row
        // (the USE fork's non-Closet doors) -- every signal on that
        // row becomes a named trigger in capture order, and origin
        // defaults to "remote" server-side when this is set and origin
        // is omitted. Manual-tab creation (Track 2 3) omits this
        // entirely, exactly as before.
        promoted_from_unknown_id?: string | null;
    }): Promise<TriggerRemoteInfo> {
        return this.hass.connection.sendMessagePromise<TriggerRemoteInfo>({
            type: "hair/trigger-remote/create",
            ...payload,
        });
    }

    /**
     * Add Popups signpost 2, Track 3: delete a named remote (takes its
     * triggers with it, per the release-a.md ruling -- enforced
     * server-side). The dialog's only caller today is its own
     * best-effort rollback when Closet/Device seeding fails partway
     * through the create loop.
     */
    deleteTriggerRemote(remoteId: string): Promise<{ removed: boolean }> {
        return this.hass.connection.sendMessagePromise<{ removed: boolean }>({
            type: "hair/trigger-remote/delete",
            remote_id: remoteId,
        });
    }

    /**
     * Add Popups signpost 2, Track 4: list all named trigger remotes
     * (the HAIR Triggers drawer is separate -- getTriggerDrawer() /
     * listTriggers() cover it). Track 3 deliberately left this
     * unwritten ("no caller yet"); the Trigger Remotes section's card
     * list and its + Add button's post-create/-delete refresh are that
     * caller now.
     */
    listTriggerRemotes(): Promise<TriggerRemoteInfo[]> {
        return this.hass.connection.sendMessagePromise<TriggerRemoteInfo[]>({
            type: "hair/trigger-remotes",
        });
    }

    /**
     * Add Popups signpost 2, Track 5: rename a named remote (the
     * expand view's header rename-in-place, same pattern as
     * renameTriggerDrawer above but scoped to one remote_id).
     */
    renameTriggerRemote(
        remoteId: string,
        name: string,
    ): Promise<TriggerRemoteInfo> {
        return this.hass.connection.sendMessagePromise<TriggerRemoteInfo>({
            type: "hair/trigger-remote/rename",
            remote_id: remoteId,
            name,
        });
    }

    /**
     * Add Popups signpost 2, Track 5: clone a named remote AND its
     * triggers under a new name (owner ruling 2026-08-14 -- unlike
     * duplicateDevice above, this one's triggers ARE copied; see
     * ir-duplicate-trigger-remote-dialog.ts and the backend
     * ws_duplicate_trigger_remote docstring for the full semantics).
     */
    duplicateTriggerRemote(
        remoteId: string,
        newName: string,
        // Track 2 item 6: the duplicate dialog footer's receiver-chip
        // picker override. Omit to inherit the source's scope
        // unchanged (the pre-item-6 default); pass a list, including
        // an empty one, to set it explicitly.
        receiverScope?: string[],
    ): Promise<TriggerRemoteInfo> {
        const msg: Record<string, unknown> = {
            type: "hair/trigger-remote/duplicate",
            remote_id: remoteId,
            new_name: newName,
        };
        if (receiverScope !== undefined) msg.receiver_scope = receiverScope;
        return this.hass.connection.sendMessagePromise<TriggerRemoteInfo>(msg);
    }

    /**
     * Add Popups signpost 2, Track 5 follow-up (owner bench request,
     * 2026-08-14): set a named remote's receiver_scope after creation
     * -- the expand view's own ir-receiver-picker, mirroring
     * ir-device-detail.ts's emitter picker up top. Remote-level only,
     * same field the Add Trigger Remote dialog's footer picker
     * already writes at creation.
     */
    setTriggerRemoteReceiverScope(
        remoteId: string,
        receiverScope: string[],
    ): Promise<TriggerRemoteInfo> {
        return this.hass.connection.sendMessagePromise<TriggerRemoteInfo>({
            type: "hair/trigger-remote/set-receiver-scope",
            remote_id: remoteId,
            receiver_scope: receiverScope,
        });
    }

    /**
     * Pin storage (signpost 3, Track 2 item 5 / section 0b): add a
     * device to a remote's pinned_device_ids. Storage only -- no
     * retransmit/derivation behavior until signpost 4. First real
     * caller is ir-pin-prompt-dialog.ts's "Pin" button (Track 3.5);
     * the header Pin: chip group stays a readonly preview
     * (PINNING_UI_ENABLED) until that signpost.
     */
    pinTriggerRemoteDevice(
        remoteId: string,
        deviceId: string,
    ): Promise<{ pinned_device_ids: string[] }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/trigger-remote/pin",
            remote_id: remoteId,
            device_id: deviceId,
        });
    }

    /** Unpin, the reverse of pinTriggerRemoteDevice above. Not yet
     *  called anywhere (the chip group that will call it is gated),
     *  added alongside pin for symmetry. */
    unpinTriggerRemoteDevice(
        remoteId: string,
        deviceId: string,
    ): Promise<{ pinned_device_ids: string[] }> {
        return this.hass.connection.sendMessagePromise({
            type: "hair/trigger-remote/unpin",
            remote_id: remoteId,
            device_id: deviceId,
        });
    }

    /**
     * Add Popups signpost 2, Track 3: a wig's discrete-signal identities
     * (matrix cells excluded -- see the backend docstring), for the Add
     * Trigger Remote dialog's Closet tab to seed one createTrigger()
     * call per signal. Same EITHER/OR source shape wigMakeDevice uses.
     */
    wigSignals(
        source: { filename: string } | { codebookId: string },
    ): Promise<{ signals: WigSignalIdentity[] }> {
        return this.hass.connection.sendMessagePromise<{ signals: WigSignalIdentity[] }>({
            type: "hair/wigs/signals",
            ...("filename" in source
                ? { filename: source.filename }
                : { codebook_id: source.codebookId }),
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
     * Persist a new order for the HAIR Triggers drawer's row list
     * (Track B). ``triggerIds`` must list every trigger currently in
     * the drawer exactly once; the backend rejects a mismatched set
     * with ``invalid_format``. Mirrors ``reorderDevices``/
     * ``reorderCommands``.
     */
    reorderTriggers(triggerIds: string[]): Promise<{ reordered: boolean }> {
        return this.hass.connection.sendMessagePromise<{ reordered: boolean }>({
            type: "hair/trigger/reorder",
            trigger_ids: triggerIds,
        });
    }

    /** The HAIR Triggers drawer's identity (Track B header). */
    getTriggerDrawer(): Promise<TriggerDrawerInfo> {
        return this.hass.connection.sendMessagePromise<TriggerDrawerInfo>({
            type: "hair/trigger-drawer",
        });
    }

    /** Rename the HAIR Triggers drawer (header rename-in-place). */
    renameTriggerDrawer(name: string): Promise<TriggerDrawerInfo> {
        return this.hass.connection.sendMessagePromise<TriggerDrawerInfo>({
            type: "hair/trigger-drawer/rename",
            name,
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
