/*************************************************************************
* ADOBE CONFIDENTIAL
* ___________________
*
*  Copyright 2015 Adobe Systems Incorporated
*  All Rights Reserved.
*
* NOTICE:  All information contained herein is, and remains
* the property of Adobe Systems Incorporated and its suppliers,
* if any.  The intellectual and technical concepts contained
* herein are proprietary to Adobe Systems Incorporated and its
* suppliers and are protected by all applicable intellectual property laws,
* including trade secret and or copyright laws.
* Dissemination of this information or reproduction of this material
* is strictly forbidden unless prior written permission is obtained
* from Adobe Systems Incorporated.
**************************************************************************/
import{floodgate as t}from"./floodgate.js";import{util as e}from"./util.js";import{setExperimentCodeForAnalytics as o,removeExperimentCodeForAnalytics as a}from"../common/experimentUtils.js";import{dcLocalStorage as n}from"../common/local-storage.js";async function i(i){const[l,r,c]=await Promise.all([t.hasFlag("dc-cv-gmail-convert-to-pdf"),t.hasFlag("dc-cv-gmail-convert-to-pdf-fte"),t.hasFlag("dc-cv-gmail-convert-to-pdf-control")]),s=t.getFeatureMeta("dc-cv-gmail-convert-to-pdf-fte"),m=t.getFeatureMeta("dc-cv-gmail-convert-to-pdf");let f,p;try{f=JSON.parse(s),p=JSON.parse(m)}catch(t){}const g="en-US"===n.getItem("locale")||"en-GB"===n.getItem("locale");a("GCP"),a("GCPC"),l&&g?o("GCP"):c&&g&&o("GCPC");const T=await async function(e){const o=[];let a={};const n=e.map((async e=>{const n=`dc-cv-gmail-${e}-metadata`;if(!await t.hasFlag(n))return;const i=t.getFeatureMeta(n);if(!i)return;let l;try{l=JSON.parse(i)}catch(t){}l?.selectors?.forEach((t=>o.push(t))),a={...a,...l?.types}}));return await Promise.all(n),{selectors:o,fileExtToMimeTypeMap:a}}(p?.fileTypes||[]);i({enableConvertToPdfTouchpointInGmail:l&&g,enableGmailConvertToPdfFteToolTip:r&&g,acrobatTouchPointText:e.getTranslation("gmailConvertToPdf"),fteTooltipStrings:{title:e.getTranslation("gmailConvertToPdfFteToolTipTitle"),description:e.getTranslation("gmailConvertToPdfFteToolTipDescription"),button:e.getTranslation("closeButton")},fteConfig:f,metadata:T})}export{i as gmailConvertToPdfInit};