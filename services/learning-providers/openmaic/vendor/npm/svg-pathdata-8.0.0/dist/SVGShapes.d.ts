import { SVGPathData } from './SVGPathData.js';
/**
 * Creates an ellipse path centered at (cx,cy) with radii rx and ry
 */
declare function createEllipse(rx: number, ry: number, cx: number, cy: number): SVGPathData;
/**
 * Creates a rectangle path with optional rounded corners
 */
declare function createRect(x: number, y: number, width: number, height: number, rX?: number, rY?: number): SVGPathData;
/**
 * Creates a polyline from an array of coordinates [x1,y1,x2,y2,...]
 */
declare function createPolyline(coords: number[]): SVGPathData;
/**
 * Creates a closed polygon from an array of coordinates
 */
declare function createPolygon(coords: number[]): SVGPathData;
export declare const SVGShapes: {
    createEllipse: typeof createEllipse;
    createRect: typeof createRect;
    createPolyline: typeof createPolyline;
    createPolygon: typeof createPolygon;
};
export {};
