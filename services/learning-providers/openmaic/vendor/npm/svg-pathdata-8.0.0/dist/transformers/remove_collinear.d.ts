import type { SVGCommand } from '../types.js';
/**
 * Process a path and remove collinear points
 * @param commands Array of SVG path commands to process (must be absolute)
 * @returns New array with collinear points removed
 */
export declare function REMOVE_COLLINEAR(commands: SVGCommand[]): SVGCommand[];
