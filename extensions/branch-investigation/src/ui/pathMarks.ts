import { CodeAnchor, Range, WorkspaceDocument } from '../domain/model';
import { activeRoute } from './tracePresentation';

export interface PathMark { line: number; label: string; current: boolean }

/**
 * Investigation numbers of the active route for one open file, one mark per line.
 * A step is marked only where the saved range still holds the saved text: edited or shifted code gets no number rather than a wrong line.
 * Numbers are investigation order, never execution order.
 */
export function pathMarks(document: WorkspaceDocument, inFile: (anchor: CodeAnchor) => boolean, textAt: (range: Range) => string): PathMark[] {
  const marks = new Map<number, PathMark>();
  for (const step of activeRoute(document)) {
    const anchor = document.anchors.find(a => a.id === step.codeAnchorId);
    if (!anchor?.range || !inFile(anchor) || textAt(anchor.range) !== step.snippet) { continue; }
    const mark = marks.get(anchor.range.start.line) ?? { line: anchor.range.start.line, label: '조사', current: false };
    mark.label += ` #${step.sequence}`; mark.current ||= step.id === document.currentStepId; marks.set(mark.line, mark);
  }
  return [...marks.values()];
}
