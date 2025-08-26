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
import{floodgate as t}from"./floodgate.js";import{dcLocalStorage as e}from"../common/local-storage.js";import{setExperimentCodeForAnalytics as o,removeExperimentCodeForAnalytics as n}from"../common/experimentUtils.js";import{util as i}from"./util.js";async function a(a,l){await e.init();const[r,c]=await Promise.all([t.hasFlag("dc-cv-linkedin-pdf-touch-point"),t.hasFlag("dc-cv-linkedin-pdf-touch-point-control")]);let s,d,m,p,u;a.initializeViewerVariables();const f="false"===e.getItem("acrobat-touch-points-in-other-surfaces");try{const o=JSON.parse(t.getFeatureMeta("dc-cv-linkedin-pdf-touch-point"));s=o?o.selectors:{},d=!!o&&o.fteEnabled,m=!!o&&o.enLocaleEnabled,p=!!o&&o.nonEnLocaleEnabled,u=((t,o)=>{const n="en-US"===e.getItem("locale")||"en-GB"===e.getItem("locale");return n&&t||!n&&o})(m,p)}catch(t){s={},d=!1,u=!1}return r&&u?(n("LIC"),o("LI")):c&&u?(n("LI"),o("LIC")):(n("LI"),n("LIC")),{enableLinkedinPDFTouchPoint:r&&!f&&u,selectors:s,touchPointString:i.getTranslation("gsuiteOpenWithAcrobat"),fteToolTipStrings:{title:i.getTranslation("outlookPDFTouchPointFTEHeader"),description:i.getTranslation("linkedInFeedPDFTouchPointFTEBody"),button:i.getTranslation("closeButton")},enableLinkedinFteTooltip:d,frameId:l?.frameId}}export{a as linkedinInit};