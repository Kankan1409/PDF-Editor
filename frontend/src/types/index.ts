export interface TextLine {id:string;text:string;bbox:number[];origin:number[];font:string;size:number;color:string;flags:number;editable:boolean;mixed:boolean}
export interface PageInfo {index:number;width:number;height:number;base_width:number;base_height:number;rotation:number;kind:string;lines:TextLine[]}
export interface DocumentInfo {name:string;revision:number;pages:PageInfo[];page_count:number;size:number;editable:boolean;warnings:string[];can_undo:boolean;can_redo:boolean}
export interface PreviewInfo {preview_id:string;warnings:string[];pages:PageInfo[];page_count:number}
export interface Hit {page:number;line_id:string;start:number;before:string;bbox:number[]}
export interface Operation {kind:string;font_name?:string;page?:number;line_id?:string;text?:string;query?:string;all?:boolean;start?:number;rect?:number[];size?:number;color?:string;order?:number[]}
