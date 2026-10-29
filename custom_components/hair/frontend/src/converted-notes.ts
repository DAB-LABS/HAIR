/**
 * The notes a converted paste carries past its carrier line.
 *
 * When a paste in another format converts, the server answers with the
 * carrier note first and then whatever else the conversion asks to be
 * said (a repeat count the source set, for one), ahead of the Pronto
 * validator's own warnings. The editor puts the converted Pronto in the
 * box and validates it again, and that second answer carries only the
 * validator's warnings. This keeps the conversion's notes: everything
 * the first answer said after its carrier line that the second does
 * not say, in front of the second answer's warnings. The carrier line
 * itself is left out, since the converted line under the box says it.
 *
 * Pure and import-free, so tests/test_converted_notes_js.py runs it
 * under node.
 */
export function keepConversionNotes(first: string[], second: string[]): string[] {
    const notes = first.slice(1).filter((note) => !second.includes(note));
    return [...notes, ...second];
}
