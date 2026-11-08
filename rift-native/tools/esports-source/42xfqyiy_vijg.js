(globalThis.TURBOPACK||(globalThis.TURBOPACK=[])).push(["object"==typeof document?document.currentScript:void 0,645112,e=>{"use strict";var t=e.i(842157),r=e.i(428615);let a=t.use||function(e){let t=(0,r.decoratePromise)(e);switch(t.status){case"pending":throw t;case"rejected":throw t.reason;case"fulfilled":return t.value}};e.s(["__use",0,a])},950954,e=>{"use strict";var t=e.i(842157),r=e.i(569179),a=e.i(28912);e.s(["useSuspenseHookCacheKey",0,function(e,s){let{queryKey:n=[],variables:o}=s,i=(0,r.canonicalStringify)(o),[l,c]=t.useState(i);return s!==a.skipToken&&l!==i&&c(l=i),[e,l,...[].concat(n)]}])},562882,e=>{"use strict";var t=e.i(842157),r=e.i(165687),a=e.i(897490),s=e.i(620840),n=e.i(139350),o=e.i(28912),i=e.i(645112),l=e.i(329945),c=e.i(950954),u=e.i(639823),d=e.i(616682),m=e.i(623473);function p(e,s){let n=(0,m.useApolloClient)(s.client),o=(0,a.getSuspenseCache)(n),l=h({client:n,query:e,options:s}),{fetchPolicy:u}=l,d=(0,c.useSuspenseHookCacheKey)(e,s),p=o.getQueryRef(d,()=>n.watchQuery(l)),[f,g]=t.useState([p.key,p.promise]);f[0]!==p.key&&(f[0]=p.key,f[1]=p.promise);let v=f[1];p.didChangeOptions(l)&&(f[1]=v=p.applyOptions(l)),t.useEffect(()=>{let e=p.retain(),t=p.listen(e=>{g([p.key,e])});return()=>{t(),e()}},[p]);let y=t.useMemo(()=>{let e=p.result.error,t=!!p.result.data;return{loading:!1,data:p.result.data,dataState:p.result.dataState,networkStatus:e?r.NetworkStatus.error:r.NetworkStatus.ready,error:e,complete:t,partial:!t}},[p.result]),w="standby"===u?y:(0,i.__use)(v),S=t.useCallback(e=>{let t=p.fetchMore(e);return g([p.key,p.promise]),t},[p]),b=t.useCallback(e=>{let t=p.refetch(e);return g([p.key,p.promise]),t},[p]),x=p.observable.subscribeToMore;return t.useMemo(()=>({client:n,data:w.data,dataState:w.dataState,error:w.error,networkStatus:w.networkStatus,fetchMore:S,refetch:b,subscribeToMore:x}),[n,S,b,w,x])}function h({client:e,query:t,options:r}){return(0,l.useDeepMemo)(()=>{if(r===o.skipToken)return{query:t,fetchPolicy:"standby",[n.variablesUnknownSymbol]:!0};let a=r.fetchPolicy||e.defaultOptions.watchQuery?.fetchPolicy||"cache-first",i={...r,fetchPolicy:a,query:t,notifyOnNetworkStatusChange:!1,nextFetchPolicy:void 0};return s.__DEV__&&function(e){var t,r;let{fetchPolicy:a,returnPartialData:n}=e;(function(e="cache-first"){(0,d.invariant)(["cache-first","network-only","no-cache","cache-and-network"].includes(e),35,e)})(a),t=a,r=n,"no-cache"===t&&r&&s.__DEV__&&d.invariant.warn(36)}(i),r.skip&&(i.fetchPolicy="standby"),i},[e,r,t])}e.s(["useSuspenseQuery",0,function(e,t){return(0,u.wrapHook)("useSuspenseQuery",p,(0,m.useApolloClient)("object"==typeof t?t.client:void 0))(e,t??{})},"useWatchQueryOptions",0,h],562882)},897490,e=>{"use strict";var t=e.i(336419),r=e.i(240957),a=e.i(291262),s=e.i(428615);class n{observable;key={};promise;resolve;reject;subscription;listeners=new Set;autoDisposeTimeoutId;references=0;constructor(e,t,r){this.dispose=this.dispose.bind(this),this.handleNext=this.handleNext.bind(this),this.handleError=this.handleError.bind(this),this.observable=e.watchFragment(t),r.onDispose&&(this.onDispose=r.onDispose);const s=this.observable.getCurrentResult(),n=()=>{this.references||(this.autoDisposeTimeoutId=setTimeout(this.dispose,r.autoDisposeTimeoutMs??3e4))};this.promise=s.complete?(0,a.createFulfilledPromise)(s.data):this.createPendingPromise(),this.subscribeToFragment(),this.promise.then(n,n)}listen(e){return this.listeners.add(e),()=>{this.listeners.delete(e)}}retain(){this.references++,clearTimeout(this.autoDisposeTimeoutId);let e=!1;return()=>{e||(e=!0,this.references--,setTimeout(()=>{this.references||this.dispose()}))}}dispose(){this.subscription.unsubscribe()}onDispose(){}subscribeToFragment(){this.subscription=this.observable.subscribe(this.handleNext.bind(this),this.handleError.bind(this)),this.subscription.add(this.onDispose)}handleNext(e){switch(this.promise.status){case"pending":if(e.complete)return this.resolve?.(e.data);this.deliver(this.promise);break;case"fulfilled":if((0,r.equal)(this.promise.value,e.data))return;this.promise=e.complete?(0,a.createFulfilledPromise)(e.data):this.createPendingPromise(),this.deliver(this.promise)}}handleError(e){this.reject?.(e)}deliver(e){this.listeners.forEach(t=>t(e))}createPendingPromise(){return(0,s.decoratePromise)(new Promise((e,t)=>{this.resolve=e,this.reject=t}))}}var o=e.i(44894);class i{queryRefs=new t.Trie;fragmentRefs=new t.Trie;options;constructor(e={}){this.options=e}getQueryRef(e,t){let r=this.queryRefs.lookupArray(e);return r.current||(r.current=new o.InternalQueryReference(t(),{autoDisposeTimeoutMs:this.options.autoDisposeTimeoutMs,onDispose:()=>{delete r.current}})),r.current}getFragmentRef(e,t,r){let a=this.fragmentRefs.lookupArray(e);return a.current||(a.current=new n(t,r,{autoDisposeTimeoutMs:this.options.autoDisposeTimeoutMs,onDispose:()=>{delete a.current}})),a.current}add(e,t){this.queryRefs.lookupArray(e).current=t}}let l=Symbol.for("apollo.suspenseCache");e.s(["getSuspenseCache",0,function(e){return e[l]||(e[l]=new i(e.defaultOptions.react?.suspense)),e[l]}],897490)},875275,e=>{"use strict";var t=e.i(842157),r=e.i(543836),a=e.i(728654),s=e.i(652531),n=e.i(548913),o=e.i(686575),i=e.i(45240),l=e.i(327126),c=Object.defineProperty,u=(e,t)=>c(e,"name",{value:t,configurable:!0}),d="Switch",[m,p]=(0,s.createContextScope)(d),[h,f]=m(d);function g(e){let{__scopeSwitch:r,checked:a,children:s,defaultChecked:o,disabled:i,form:c,name:u,onCheckedChange:m,required:p,value:f="on",internal_do_not_use_render:g}=e,[v,y]=(0,n.useControllableState)({prop:a,defaultProp:o??!1,onChange:m,caller:d}),[w,S]=t.useState(null),[x,T]=t.useState(null),k=t.useRef(!1),[C,D]=t.useReducer(e=>e+1,0),E=!w||!!c||!!w.closest("form"),R={checked:v,setChecked:y,disabled:i,control:w,setControl:S,name:u,form:c,value:f,hasConsumerStoppedPropagationRef:k,userInteractionCount:C,onUserInteraction:D,required:p,defaultChecked:o,isFormControl:E,bubbleInput:x,setBubbleInput:T};return(0,l.jsx)(h,{scope:r,...R,children:b(g)?g(R):s})}u(g,"SwitchProvider");var v=t.forwardRef(u(function({__scopeSwitch:e,onClick:s,...n},o){let{control:c,form:d,value:m,disabled:p,checked:h,required:g,setControl:v,setChecked:y,hasConsumerStoppedPropagationRef:w,onUserInteraction:S,isFormControl:b,bubbleInput:T}=f("SwitchTrigger",e),k=(0,a.useComposedRefs)(o,v),C=t.useRef(h);return t.useEffect(()=>{let e=d?c?.ownerDocument.getElementById(d):c?.form;if(e instanceof HTMLFormElement){let t=u(()=>y(C.current),"reset");return e.addEventListener("reset",t),()=>e.removeEventListener("reset",t)}},[c,d,y]),(0,l.jsx)(i.Primitive.button,{type:"button",role:"switch","aria-checked":h,"aria-required":g,"data-state":x(h),"data-disabled":p?"":void 0,disabled:p,value:m,...n,ref:k,onClick:(0,r.composeEventHandlers)(s,e=>{S(),y(e=>!e),T&&b&&(w.current=e.isPropagationStopped(),w.current||e.stopPropagation())})})},"SwitchTrigger")),y=t.forwardRef(u(function(e,t){let{__scopeSwitch:r,name:a,checked:s,defaultChecked:n,required:o,disabled:i,value:c,onCheckedChange:u,form:d,...m}=e;return(0,l.jsx)(g,{__scopeSwitch:r,checked:s,defaultChecked:n,disabled:i,required:o,onCheckedChange:u,name:a,form:d,value:c,internal_do_not_use_render:({isFormControl:e})=>(0,l.jsxs)(l.Fragment,{children:[(0,l.jsx)(v,{...m,ref:t,__scopeSwitch:r}),e&&(0,l.jsx)(S,{__scopeSwitch:r})]})})},"Switch")),w=t.forwardRef(u(function(e,t){let{__scopeSwitch:r,...a}=e,s=f("SwitchThumb",r);return(0,l.jsx)(i.Primitive.span,{"data-state":x(s.checked),"data-disabled":s.disabled?"":void 0,...a,ref:t})},"SwitchThumb")),S=t.forwardRef(u(function({__scopeSwitch:e,onClick:s,...n},c){let{control:u,hasConsumerStoppedPropagationRef:d,userInteractionCount:m,checked:p,defaultChecked:h,required:g,disabled:v,name:y,value:w,form:S,bubbleInput:b,setBubbleInput:x}=f("SwitchBubbleInput",e),T=(0,a.useComposedRefs)(c,x),k=(0,o.useSize)(u),C=t.useRef(!1),D=t.useRef(p),E=t.useRef(m);t.useEffect(()=>{if(!b)return;let e=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,"checked").set,t=m!==E.current;E.current=m;let r=D.current!==p;D.current=p;let a=!(t&&d.current);if(r&&e){C.current=!t;let r=new Event("click",{bubbles:a});e.call(b,p),b.dispatchEvent(r),C.current=!1}},[b,p,d,m]);let R=t.useRef(p);return(0,l.jsx)(i.Primitive.input,{type:"checkbox","aria-hidden":!0,defaultChecked:h??R.current,required:g,disabled:v,name:y,value:w,form:S,...n,tabIndex:-1,ref:T,onClick:(0,r.composeEventHandlers)(s,e=>{C.current&&e.stopPropagation()}),style:{...n.style,...k,position:"absolute",pointerEvents:"none",opacity:0,margin:0,transform:"translateX(-100%)"}})},"SwitchBubbleInput"));function b(e){return"function"==typeof e}function x(e){return e?"checked":"unchecked"}u(b,"isFunction"),u(x,"getState"),e.s(["Root",0,y,"Switch",0,y,"SwitchThumb",0,w,"Thumb",0,w,"createSwitchScope",0,p,"unstable_BubbleInput",0,S,"unstable_Provider",0,g,"unstable_SwitchBubbleInput",0,S,"unstable_SwitchProvider",0,g,"unstable_SwitchTrigger",0,v,"unstable_Trigger",0,v],278266);var T=e.i(278266);e.s(["Switch",0,T],875275)},961341,e=>{"use strict";var t=e.i(327126),r=e.i(842157),a=e.i(779118),s=e.i(779923),n=e.i(682025),o=e.i(323908),i=e.i(920479),l=r,c=e.i(272596);function u(e,t){if("function"==typeof e)return e(t);null!=e&&(e.current=t)}class d extends l.Component{getSnapshotBeforeUpdate(e){let t=this.props.childRef.current;if((0,i.isHTMLElement)(t)&&e.isPresent&&!this.props.isPresent&&!1!==this.props.pop){let e=t.offsetParent,r=(0,i.isHTMLElement)(e)&&e.offsetWidth||0,a=(0,i.isHTMLElement)(e)&&e.offsetHeight||0,s=getComputedStyle(t),n=this.props.sizeRef.current;n.height=parseFloat(s.height),n.width=parseFloat(s.width),n.top=t.offsetTop,n.left=t.offsetLeft,n.right=r-n.width-n.left,n.bottom=a-n.height-n.top,n.direction=s.direction}return null}componentDidUpdate(){}render(){return this.props.children}}function m({children:e,isPresent:a,anchorX:s,anchorY:n,root:o,pop:i}){let p=(0,l.useId)(),h=(0,l.useRef)(null),f=(0,l.useRef)({width:0,height:0,top:0,left:0,right:0,bottom:0,direction:"ltr"}),{nonce:g}=(0,l.useContext)(c.MotionConfigContext),v=function(...e){return r.useCallback(function(...e){return t=>{let r=!1,a=e.map(e=>{let a=u(e,t);return r||"function"!=typeof a||(r=!0),a});if(r)return()=>{for(let t=0;t<a.length;t++){let r=a[t];"function"==typeof r?r():u(e[t],null)}}}}(...e),e)}(h,!1!==i?e.props?.ref??e?.ref:void 0);return(0,l.useInsertionEffect)(()=>{let{width:e,height:t,top:r,left:l,right:c,bottom:u,direction:d}=f.current;if(a||!1===i||!h.current||!e||!t)return;let m="rtl"===d,v="left"===s?m?`right: ${c}`:`left: ${l}`:m?`left: ${l}`:`right: ${c}`,y="bottom"===n?`bottom: ${u}`:`top: ${r}`;h.current.dataset.motionPopId=p;let w=document.createElement("style");g&&(w.nonce=g);let S=o??document.head;return S.appendChild(w),w.sheet&&w.sheet.insertRule(`
          [data-motion-pop-id="${p}"] {
            position: absolute !important;
            width: ${e}px !important;
            height: ${t}px !important;
            ${v}px !important;
            ${y}px !important;
          }
        `),()=>{h.current?.removeAttribute("data-motion-pop-id"),S.contains(w)&&S.removeChild(w)}},[a]),(0,t.jsx)(d,{isPresent:a,childRef:h,sizeRef:f,pop:i,children:!1===i?e:l.cloneElement(e,{ref:v})})}let p=({children:e,initial:a,isPresent:i,onExitComplete:l,custom:c,presenceAffectsLayout:u,mode:d,anchorX:p,anchorY:f,root:g})=>{let v=(0,s.useConstant)(h),y=(0,r.useId)(),w=(0,r.useRef)(i),S=(0,r.useRef)(l);(0,n.useIsomorphicLayoutEffect)(()=>{w.current=i,S.current=l});let b=!0,x=(0,r.useMemo)(()=>(b=!1,{id:y,initial:a,isPresent:i,custom:c,onExitComplete:e=>{for(let t of(v.set(e,!0),v.values()))if(!t)return;l&&l()},register:e=>(v.set(e,!1),()=>{v.delete(e),w.current||v.size||S.current?.()})}),[i,v,l]);return u&&b&&(x={...x}),(0,r.useMemo)(()=>{v.forEach((e,t)=>v.set(t,!1))},[i]),r.useEffect(()=>{i||v.size||!l||l()},[i]),e=(0,t.jsx)(m,{pop:"popLayout"===d,isPresent:i,anchorX:p,anchorY:f,root:g,children:e}),(0,t.jsx)(o.PresenceContext.Provider,{value:x,children:e})};function h(){return new Map}var f=e.i(614253);let g=e=>e.key||"";function v(e){let t=[];return r.Children.forEach(e,e=>{(0,r.isValidElement)(e)&&t.push(e)}),t}e.s(["AnimatePresence",0,({children:e,custom:o,initial:i=!0,onExitComplete:l,presenceAffectsLayout:c=!0,mode:u="sync",propagate:d=!1,anchorX:m="left",anchorY:h="top",root:y})=>{let[w,S]=(0,f.usePresence)(d),b=(0,r.useMemo)(()=>v(e),[e]),x=d&&!w?[]:b.map(g),T=(0,r.useRef)(!0),k=(0,r.useRef)(b),C=(0,s.useConstant)(()=>new Map),D=(0,r.useRef)(new Set),[E,R]=(0,r.useState)(b),[I,j]=(0,r.useState)(b);(0,n.useIsomorphicLayoutEffect)(()=>{T.current=!1,k.current=b;for(let e=0;e<I.length;e++){let t=g(I[e]);x.includes(t)?(C.delete(t),D.current.delete(t)):!0!==C.get(t)&&C.set(t,!1)}},[I,x.length,x.join("-")]);let _=[];if(b!==E){let e=[...b];for(let t=0;t<I.length;t++){let r=I[t],a=g(r);x.includes(a)||(e.splice(t,0,r),_.push(r))}return"wait"===u&&_.length&&(e=_),j(v(e)),R(b),null}let{forceRender:P}=(0,r.useContext)(a.LayoutGroupContext);return(0,t.jsx)(t.Fragment,{children:I.map(e=>{let r=g(e),a=(!d||!!w)&&(b===I||x.includes(r));return(0,t.jsx)(p,{isPresent:a,initial:(!T.current||!!i)&&void 0,custom:o,presenceAffectsLayout:c,mode:u,root:y,onExitComplete:a?void 0:()=>{if(D.current.has(r)||!C.has(r))return;D.current.add(r),C.set(r,!0);let e=!0;C.forEach(t=>{t||(e=!1)}),e&&(P?.(),j(k.current),d&&S?.(),l&&l())},anchorX:m,anchorY:h,children:e},r)})})}],961341)},390415,e=>{"use strict";var t=e.i(790660),r=e.i(414440),a=e.i(842157);e.s(["useReducedMotion",0,function(){t.hasReducedMotionListener.current||(0,r.initPrefersReducedMotion)();let[e]=(0,a.useState)(t.prefersReducedMotion.current);return e}])},915279,e=>{"use strict";var t=e.i(842157);let r=(0,t.createContext)(null),a={didCatch:!1,error:null};class s extends t.Component{constructor(e){super(e),this.resetErrorBoundary=this.resetErrorBoundary.bind(this),this.state=a}static getDerivedStateFromError(e){return{didCatch:!0,error:e}}resetErrorBoundary(){let{error:e}=this.state;if(null!==e){for(var t,r,s=arguments.length,n=Array(s),o=0;o<s;o++)n[o]=arguments[o];null==(t=(r=this.props).onReset)||t.call(r,{args:n,reason:"imperative-api"}),this.setState(a)}}componentDidCatch(e,t){var r,a;null==(r=(a=this.props).onError)||r.call(a,e,t)}componentDidUpdate(e,t){let{didCatch:r}=this.state,{resetKeys:s}=this.props;if(r&&null!==t.error&&function(){let e=arguments.length>0&&void 0!==arguments[0]?arguments[0]:[],t=arguments.length>1&&void 0!==arguments[1]?arguments[1]:[];return e.length!==t.length||e.some((e,r)=>!Object.is(e,t[r]))}(e.resetKeys,s)){var n,o;null==(n=(o=this.props).onReset)||n.call(o,{next:s,prev:e.resetKeys,reason:"keys"}),this.setState(a)}}render(){let{children:e,fallbackRender:a,FallbackComponent:s,fallback:n}=this.props,{didCatch:o,error:i}=this.state,l=e;if(o){let e={error:i,resetErrorBoundary:this.resetErrorBoundary};if("function"==typeof a)l=a(e);else if(s)l=(0,t.createElement)(s,e);else if(void 0!==n)l=n;else throw i}return(0,t.createElement)(r.Provider,{value:{didCatch:o,error:i,resetErrorBoundary:this.resetErrorBoundary}},l)}}e.s(["ErrorBoundary",0,s])},112476,e=>{"use strict";var t,r=e.i(842157);function a(){return(a=Object.assign.bind()).apply(null,arguments)}e.s(["default",0,function(e){return r.createElement("svg",a({xmlns:"http://www.w3.org/2000/svg",width:12,height:10,fill:"none",viewBox:"0 0 12 10"},e),t||(t=r.createElement("path",{fill:"#000",d:"M4 10 0 5.745l1.4-1.49L4 7.021 10.6 0 12 1.49z"})))}])},470410,e=>{"use strict";var t,r=e.i(842157);function a(){return(a=Object.assign.bind()).apply(null,arguments)}e.s(["default",0,function(e){return r.createElement("svg",a({xmlns:"http://www.w3.org/2000/svg",width:14,height:14,fill:"none",viewBox:"0 0 14 14"},e),t||(t=r.createElement("path",{fill:"#fff",d:"M6.993.333A6.663 6.663 0 0 0 .333 7c0 3.68 2.98 6.666 6.66 6.666A6.67 6.67 0 0 0 13.667 7 6.67 6.67 0 0 0 6.993.333m4.62 4H9.647a10.4 10.4 0 0 0-.92-2.373 5.35 5.35 0 0 1 2.886 2.373M7 1.693c.56.808.99 1.699 1.273 2.64H5.727A9.4 9.4 0 0 1 7 1.693m-5.16 6.64A5.5 5.5 0 0 1 1.667 7c0-.46.066-.907.173-1.334h2.253Q4.005 6.33 4 7c0 .453.04.893.093 1.333zm.547 1.333h1.966c.214.834.52 1.634.92 2.374a5.33 5.33 0 0 1-2.886-2.374m1.966-5.333H2.387A5.33 5.33 0 0 1 5.273 1.96c-.402.75-.711 1.547-.92 2.373M7 12.306a9.4 9.4 0 0 1-1.273-2.64h2.546A9.4 9.4 0 0 1 7 12.306m1.56-3.973H5.44Q5.343 7.669 5.333 7c0-.454.047-.9.107-1.334h3.12c.06.434.107.88.107 1.334 0 .453-.047.893-.107 1.333m.167 3.707c.402-.75.711-1.548.92-2.374h1.966a5.35 5.35 0 0 1-2.886 2.374m1.18-3.707C9.96 7.893 10 7.453 10 7c0-.454-.04-.894-.093-1.334h2.253c.107.427.173.874.173 1.334s-.066.906-.173 1.333z"})))}])},566572,e=>{"use strict";var t,r=e.i(842157);function a(){return(a=Object.assign.bind()).apply(null,arguments)}e.s(["default",0,function(e){return r.createElement("svg",a({xmlns:"http://www.w3.org/2000/svg",width:12,height:12,fill:"none",viewBox:"0 0 12 12"},e),t||(t=r.createElement("path",{fill:"currentColor",fillRule:"evenodd",d:"M4.5 1.5h3L9 3v2h1v5.5H2V5h1V3zm3 2.25V5h-3V3.75L5.25 3h1.5zM7 6.5H5V9h2z",clipRule:"evenodd"})))}])},730647,e=>{"use strict";var t,r=e.i(842157);function a(){return(a=Object.assign.bind()).apply(null,arguments)}e.s(["default",0,function(e){return r.createElement("svg",a({xmlns:"http://www.w3.org/2000/svg",width:16,height:16,fill:"none",viewBox:"0 0 16 16"},e),t||(t=r.createElement("path",{fill:"#fff",fillRule:"evenodd",d:"M12 2.666H4v.667l.667.666h-2L2 4.666v2.667l2.667 1.333v.667l2 .666-.334 2h-1l-.666.667v.667h6.666v-.667l-.666-.667h-1l-.334-2 2-.666v-.667L14 7.333V4.666l-.667-.667h-2L12 3.333zM3.333 5.333v1.333l1.334.667v-2zm9.334 1.333V5.333h-1.334v2z",clipRule:"evenodd"})))}])},939013,e=>{"use strict";var t,r,a,s,n=e.i(842157);function o(){return(o=Object.assign.bind()).apply(null,arguments)}e.s(["default",0,function(e){return n.createElement("svg",o({xmlns:"http://www.w3.org/2000/svg",width:237,height:50,fill:"none",viewBox:"0 0 237 50"},e),t||(t=n.createElement("path",{fill:"currentColor",d:"M186.33 20.533c-.02.64.06 1.28.237 1.896q.282.79.693 1.522c.087.143.138.306.146.474a.82.82 0 0 1-.407.63l-1.342.891a1.04 1.04 0 0 1-.554.185.89.89 0 0 1-.631-.299 4.8 4.8 0 0 1-.763-.98q-.313-.54-.649-1.243a7.83 7.83 0 0 1-6.233 2.934q-2.673 0-4.233-1.521a5.43 5.43 0 0 1-1.559-4.081 5.47 5.47 0 0 1 1.929-4.351q1.929-1.65 5.214-1.65 1.126.005 2.242.166 1.17.166 2.431.474v-1.583q0-2.413-1-3.394t-3.45-.986a9.6 9.6 0 0 0-2.285.28q-1.169.274-2.285.72-.359.167-.739.28a1.5 1.5 0 0 1-.337.057q-.446 0-.445-.668V9.243c-.019-.255.032-.51.147-.74.158-.196.364-.35.597-.445a14 14 0 0 1 2.673-.948 13 13 0 0 1 3.318-.408q3.792 0 5.551 1.726c1.17 1.151 1.763 2.89 1.763 5.213v6.892m-8.612 3.228a7 7 0 0 0 2.189-.389 4.7 4.7 0 0 0 2.005-1.355c.341-.391.588-.855.721-1.356a7.1 7.1 0 0 0 .204-1.839v-.891a18 18 0 0 0-1.948-.35 16 16 0 0 0-1.986-.129c-1.422 0-2.46.28-3.152.849a2.99 2.99 0 0 0-1.043 2.45 3 3 0 0 0 .782 2.247 3.05 3.05 0 0 0 2.228.763m17.006 2.308a1.35 1.35 0 0 1-.815-.199 1.7 1.7 0 0 1-.446-.839L188.52 8.612a3.7 3.7 0 0 1-.189-.853.474.474 0 0 1 .521-.521h2.081c.293-.026.586.045.834.204.215.236.362.526.427.839l3.569 14.03 3.318-14.03c.045-.316.187-.61.407-.84.256-.156.555-.227.854-.203h1.711c.298-.024.597.047.853.204.22.23.362.523.407.839l3.342 14.22 3.673-14.22c.065-.313.212-.603.427-.84.248-.158.541-.23.834-.203h1.967a.47.47 0 0 1 .497.313.5.5 0 0 1 .025.208 2 2 0 0 1-.038.337 4 4 0 0 1-.147.516l-5.143 16.41a1.66 1.66 0 0 1-.445.839c-.244.152-.53.221-.816.199h-1.82a1.3 1.3 0 0 1-.853-.223 1.56 1.56 0 0 1-.408-.853l-3.318-13.66-3.265 13.66c-.048.318-.19.615-.408.853a1.3 1.3 0 0 1-.858.223zm27.25.56a14.5 14.5 0 0 1-3.266-.37 9.6 9.6 0 0 1-2.451-.858 1.43 1.43 0 0 1-.649-.593 1.5 1.5 0 0 1-.128-.592v-1.09c0-.446.157-.664.474-.664q.201.004.389.076.2.07.535.218c.751.334 1.536.584 2.342.744.83.172 1.674.259 2.522.261a5.7 5.7 0 0 0 3.099-.706 2.25 2.25 0 0 0 1.095-2.005 2.04 2.04 0 0 0-.573-1.484 5.4 5.4 0 0 0-2.138-1.114l-3.081-.948a6.57 6.57 0 0 1-3.394-2.152 5.02 5.02 0 0 1-1.057-3.08 4.7 4.7 0 0 1 .574-2.37c.382-.681.9-1.276 1.521-1.75a6.9 6.9 0 0 1 2.209-1.094 9.5 9.5 0 0 1 2.674-.37q.713.002 1.422.095a14.3 14.3 0 0 1 2.583.573q.461.145.891.37c.242.131.456.308.63.521.134.21.198.458.185.707v1q0 .668-.474.668a2.3 2.3 0 0 1-.815-.256 9.9 9.9 0 0 0-4.081-.82 5.56 5.56 0 0 0-2.844.597 2.03 2.03 0 0 0-1 1.896 2 2 0 0 0 .63 1.503 6.4 6.4 0 0 0 2.361 1.152l3.009.948c1.536.497 2.626 1.18 3.285 2.043a4.8 4.8 0 0 1 .981 2.971 5.4 5.4 0 0 1-.554 2.47 5.6 5.6 0 0 1-1.541 1.872 6.9 6.9 0 0 1-2.37 1.185c-.977.283-1.991.422-3.009.413"})),r||(r=n.createElement("path",{fill:"currentColor",fillRule:"evenodd",d:"M226.018 37.066c-6.987 5.152-17.111 7.896-25.832 7.896a46.72 46.72 0 0 1-31.549-12.039c-.654-.587-.071-1.393.716-.948a63.5 63.5 0 0 0 31.567 8.376 62.9 62.9 0 0 0 24.084-4.925c1.18-.503 2.166.777 1.014 1.63",clipRule:"evenodd"})),a||(a=n.createElement("path",{fill:"currentColor",fillRule:"evenodd",d:"M228.942 33.748c-.896-1.142-5.906-.54-8.157-.275-.683.08-.787-.512-.171-.948 3.996-2.81 10.546-2 11.31-1.057.763.943-.204 7.513-3.949 10.65-.578.474-1.123.223-.872-.412.844-2.104 2.735-6.82 1.839-7.963",clipRule:"evenodd"})),s||(s=n.createElement("path",{fill:"currentColor",d:"M5.272 32.231a.564.564 0 0 1-.64-.64V12.158a.564.564 0 0 1 .64-.635h1.593a.673.673 0 0 1 .754.578l.175.9a7.3 7.3 0 0 1 2.247-1.421 6.9 6.9 0 0 1 2.569-.475 5.34 5.34 0 0 1 4.393 2.058q1.636 2.061 1.636 5.54a10.3 10.3 0 0 1-.796 4.205 6.3 6.3 0 0 1-2.195 2.72 5.7 5.7 0 0 1-3.247.948 6.7 6.7 0 0 1-2.37-.421 6 6 0 0 1-1.967-1.166v6.635a.564.564 0 0 1-.645.607zm6.233-8.342a3.17 3.17 0 0 0 2.759-1.26q.91-1.267.91-3.845t-.882-3.792a3.15 3.15 0 0 0-2.744-1.232 6 6 0 0 0-3.484 1.109v7.882a5.94 5.94 0 0 0 3.441 1.138M28.446 26.7q-3.366 0-5.247-2.072-1.883-2.07-1.896-5.754 0-3.682 1.896-5.745 1.896-2.061 5.247-2.057 3.36 0 5.251 2.057t1.896 5.745q0 3.682-1.896 5.754T28.446 26.7m0-2.693q3.654 0 3.654-5.133t-3.654-5.105q-3.655 0-3.655 5.105t3.655 5.133M42.276 26.268a.79.79 0 0 1-.844-.611l-4.29-13.163a2.3 2.3 0 0 1-.165-.583q0-.404.555-.403h2.37a.69.69 0 0 1 .753.55l2.75 10.693 2.815-10.664a.7.7 0 0 1 .275-.474c.165-.086.35-.125.535-.114h1.896a.95.95 0 0 1 .55.128.78.78 0 0 1 .26.45l2.816 10.873 2.901-10.901a.69.69 0 0 1 .754-.55h2.114q.554-.001.554.403-.038.3-.147.583l-4.38 13.162a.81.81 0 0 1-.838.612h-2.034a1 1 0 0 1-.55-.133.76.76 0 0 1-.289-.474l-2.754-10.465-2.734 10.47a.76.76 0 0 1-.294.474.97.97 0 0 1-.55.133zM67.74 26.7q-3.655 0-5.542-1.972-1.886-1.972-1.896-5.74 0-3.74 1.844-5.83t5.166-2.086q2.845 0 4.366 1.55t1.521 4.394q0 1.034-.147 2.057a.8.8 0 0 1-.218.512.65.65 0 0 1-.417.128h-8.944q.086 2.205 1.233 3.233 1.146 1.028 3.526 1.028a13.1 13.1 0 0 0 3.65-.55l.35-.085a.8.8 0 0 1 .204-.028c.29 0 .432.19.432.578v1.043c.016.216-.028.433-.128.625-.16.173-.366.298-.593.36-1.406.541-2.902.807-4.408.783m2.416-9.276v-.232a4.13 4.13 0 0 0-.767-2.697 2.75 2.75 0 0 0-2.247-.948 3.32 3.32 0 0 0-2.55 1.042 4.5 4.5 0 0 0-1.133 2.816zM77.162 26.268a.564.564 0 0 1-.64-.64V12.144a.563.563 0 0 1 .64-.636h1.526c.195-.017.391.023.564.114a.64.64 0 0 1 .218.436l.351 1.654a8.1 8.1 0 0 1 2.176-1.8 4.74 4.74 0 0 1 2.204-.522h.113q.318-.007.626.071a.6.6 0 0 1 .346.246c.084.203.12.422.104.64v1.565q0 .61-.526.611c-.114 0-.275 0-.474-.028-.199-.029-.417-.029-.65-.029a6.7 6.7 0 0 0-3.791 1.1v10.062a.563.563 0 0 1-.635.64zM94.387 26.7q-3.656 0-5.541-1.972-1.887-1.972-1.896-5.74 0-3.74 1.839-5.83 1.84-2.09 5.147-2.086 2.844 0 4.366 1.55t1.521 4.394q-.003 1.033-.142 2.057a.86.86 0 0 1-.218.512.66.66 0 0 1-.422.128h-8.916q.085 2.205 1.233 3.233 1.146 1.028 3.521 1.028a13.1 13.1 0 0 0 3.655-.55l.346-.085a1 1 0 0 1 .204-.028c.289 0 .436.19.436.578v1.043c.018.217-.028.434-.133.625-.16.173-.365.298-.592.36a11.7 11.7 0 0 1-4.408.783m2.436-9.276v-.232a4.13 4.13 0 0 0-.768-2.697 2.74 2.74 0 0 0-2.247-.948 3.35 3.35 0 0 0-2.555 1.042 4.5 4.5 0 0 0-1.128 2.816zM108.55 26.586a5.43 5.43 0 0 1-4.451-2.071q-1.674-2.076-1.669-5.584a10.2 10.2 0 0 1 .797-4.19 6.16 6.16 0 0 1 2.218-2.725 5.77 5.77 0 0 1 3.275-.948 6.7 6.7 0 0 1 4.238 1.507v-7.11a.563.563 0 0 1 .635-.64h2.147a.563.563 0 0 1 .64.64V25.63a.56.56 0 0 1-.159.48.57.57 0 0 1-.481.16h-1.692a.68.68 0 0 1-.759-.584l-.203-.839a6.66 6.66 0 0 1-4.536 1.74m1.071-2.697a5.88 5.88 0 0 0 3.318-1.1v-7.977a5.56 5.56 0 0 0-3.28-1.043c-1.294 0-2.247.408-2.844 1.233-.597.824-.915 2.08-.915 3.792q0 5.095 3.711 5.095zM135.884 26.586a6.6 6.6 0 0 1-2.493-.474 6.2 6.2 0 0 1-2.062-1.346l-.199.924a.68.68 0 0 1-.753.583h-1.598a.56.56 0 0 1-.612-.382.55.55 0 0 1-.023-.258V5.446a.55.55 0 0 1 .023-.258.55.55 0 0 1 .355-.357.56.56 0 0 1 .257-.025h2.147a.565.565 0 0 1 .635.64v7.352a6.9 6.9 0 0 1 4.556-1.74 5.34 5.34 0 0 1 4.393 2.057q1.636 2.063 1.64 5.541a10.2 10.2 0 0 1-.801 4.204 6.3 6.3 0 0 1-2.204 2.754 5.63 5.63 0 0 1-3.261.972m-.867-2.697a3.17 3.17 0 0 0 2.754-1.26q.896-1.267.896-3.845t-.882-3.792a3.13 3.13 0 0 0-2.74-1.232 6 6 0 0 0-3.484 1.1v7.891a5.96 5.96 0 0 0 3.456 1.138M146.7 32.587a6.4 6.4 0 0 1-1.824-.228.85.85 0 0 1-.474-.308 1.2 1.2 0 0 1-.119-.62v-.987q0-.583.474-.583.177.002.351.033.33.036.663.029a3.1 3.1 0 0 0 1.858-.474q.607-.45 1.19-2.024l.375-1.02-5.508-14.03a1.4 1.4 0 0 1-.119-.473q0-.404.527-.403h2.346a.69.69 0 0 1 .753.55l3.598 11.12 3.654-11.12a.693.693 0 0 1 .754-.55h2.204q.52-.001.521.403a1.3 1.3 0 0 1-.118.474L151.488 28.6a7.45 7.45 0 0 1-1.896 3.058 4.3 4.3 0 0 1-2.892.929"})))}])},923460,e=>{e.q("/_next/static/media/arrowLeft.3awxded8gu61w.svg")},6316,e=>{e.q("/_next/static/media/arrowRight.3c8jk5wng25ju.svg")},503673,e=>{"use strict";var t=e.i(327126),r=e.i(292746),a=e.i(465040),s=e.i(842157),n=e.i(795425),o=e.i(616557);e.i(541354);var i=e.i(251084);let l=(0,a.default)(()=>e.A(464749).then(e=>({default:e.CountdownTimerComponent})),{loadableGenerated:{modules:[895927]},ssr:!1}),c=(0,i.sva)({slots:["container","title","timer"],base:{container:{display:"flex",flexDir:"column",justifyContent:"flex-start",w:"100%",bg:"black.503/60",h:87,backdropFilter:"blur(16px)",borderRadius:4,border:"1px solid {colors.stroke.rule}",md:{border:"none"}},title:{color:"unifiedText.secondary",textStyle:"label/lg",mx:"auto",mb:12}},variants:{size:{small:{container:{p:"12px 8px",md:{w:270}},timer:{display:"flex",justifyContent:"center",gap:16}},medium:{container:{p:"12px 16px",md:{w:296}},timer:{display:"flex",justifyContent:"center",gap:24}}}},defaultVariants:{size:"medium"}});e.s(["GprCountdownWidget",0,function(e){let a,i,u,d,m,p,h,f,g=(0,r.c)(20),{endDate:v,onDone:y,variants:w}=e;g[0]===Symbol.for("react.memo_cache_sentinel")?(a=(0,n.getCurrentYearForGpr)(),g[0]=a):a=g[0];let S=a,b=w?.size;g[1]!==b?(i=c({size:b}),g[1]=b,g[2]=i):i=g[2];let x=i;g[3]===Symbol.for("react.memo_cache_sentinel")?(u={year:S},g[3]=u):u=g[3];let T=(0,o.useTranslation)("gpr.initialRankings",u),[k,C]=(0,s.useState)(!1);g[4]!==y?(d=()=>{C(!0),y?.()},g[4]=y,g[5]=d):d=g[5];let D=d;if(!(v&&!k)){let e;return g[6]===Symbol.for("react.memo_cache_sentinel")?(e=(0,t.jsx)(t.Fragment,{}),g[6]=e):e=g[6],e}return g[7]!==x.title||g[8]!==T?(m=(0,t.jsx)("div",{className:x.title,children:T}),g[7]=x.title,g[8]=T,g[9]=m):m=g[9],g[10]!==v||g[11]!==D?(p=(0,t.jsx)(l,{endDate:v,onDone:D}),g[10]=v,g[11]=D,g[12]=p):p=g[12],g[13]!==x.timer||g[14]!==p?(h=(0,t.jsx)("div",{className:x.timer,children:p}),g[13]=x.timer,g[14]=p,g[15]=h):h=g[15],g[16]!==x.container||g[17]!==m||g[18]!==h?(f=(0,t.jsxs)("div",{className:x.container,children:[m,h]}),g[16]=x.container,g[17]=m,g[18]=h,g[19]=f):f=g[19],f}])},278849,e=>{"use strict";e.s(["gprHistoryStep",0,10,"gprProductName",0,"Global Power Rankings"])},795425,e=>{"use strict";e.i(235686);var t=e.i(710553),r=e.i(92938);let a=(0,t.graphql)(`
  query GetTeamGpr(
    $step: Int
    $startDate: String
    $endDate: String
    $hl: Locale!
    $sport: Sport
  ) {
    teamGPR(
      step: $step
      startDate: $startDate
      endDate: $endDate
      hl: $hl
      sport: $sport
    ) {
      ...TeamGpr
    }
  }
`),s=(0,t.graphql)(`
  fragment TeamGpr on TeamGPR {
    id
    averageOpponentGPR
    teamMatchRecord {
      wins
      losses
    }
    teamGameRecord {
      wins
      losses
    }
    currentTeamGPR {
      gprScore
      elo
      rank
      dateCalculated
    }
    previousTeamGPR {
      gprScore
      elo
      rank
      dateCalculated
    }
    teamGPRHistory {
      gprScore
      elo
      rank
      dateCalculated
    }
    tournaments {
      ...GprTeamTournamentResult
    }
    team {
      id
      code
      image
      slug
      name
      homeLeague {
        id
        image
        name
        slug
      }
    }
  }
`),n=(0,t.graphql)(`
  fragment GprTeamTournamentResult on TeamTournamentRecord {
    id
    tournamentRecord {
      wins
      losses
    }
    tournament {
      id
      name
      slug
      startTime
      endTime
      state
      league {
        id
        name
        regionSlug
      }
      teams {
        id
      }
      standings {
        team {
          id
        }
        placement
        index
      }
    }
  }
`),o=(0,t.graphql)(`
  query GetLeagueElo(
    $hl: Locale!
    $startDate: String
    $endDate: String
    $sport: Sport
  ) {
    leagueELO(
      hl: $hl
      startDate: $startDate
      endDate: $endDate
      sport: $sport
    ) {
      id
      leagueElo
      dateCalculated
      league {
        id
        image
        name
        slug
      }
      previousYearRecord {
        wins
        losses
      }
      currentYearRecord {
        wins
        losses
      }
    }
  }
`),i=(0,t.graphql)(`
  fragment GprSeason on Season {
    id
    name
    sport
    slug
    startTime
    endTime
    splits {
      id
      name
      slug
      startTime
      endTime
    }
  }
`),l="worlds",c="champs",u="current",d=(0,t.graphql)(`
  query GetGprSeasons($hl: Locale!, $sport: Sport) {
    seasons(hl: $hl, sport: [$sport]) {
      ...GprSeason
    }
  }
`),m=[{date:g(new Date(Date.UTC(2024,10,3))),key:"gpr.endOfSplit",params:{splitName:"Worlds"},slug:l},{date:g(new Date(Date.UTC(2024,8,15))),key:"gpr.endOfSplit",slug:"split-2",params:{splitName:"Split 2"}}],p=[{date:g(new Date(Date.UTC(2025,9,5))),key:"gpr.endOfStage",slug:c,params:{stageName:"Champions Paris"}},{date:g(new Date(Date.UTC(2025,8,2))),key:"gpr.endOfStage",slug:"stage-2",params:{stageName:"Stage 2"}}];function h(){return new Date().getUTCFullYear()}function f(e,t,a){let s=parseInt(e);switch(a){case r.Sport.Lol:return t.find(e=>e.sport===r.Sport.Lol&&e.slug.includes("lolesports")&&new Date(e.endTime).getUTCFullYear()===s);case r.Sport.Val:return t.find(e=>e.sport===r.Sport.Val&&e.slug.includes("valorant_champions_tour")&&new Date(e.endTime).getUTCFullYear()===s)}}function g(e){return e.toISOString().split("T")[0]}function v(e){return e===r.Sport.Lol?l:e===r.Sport.Val?c:""}e.s(["CURRENT_MILESTONE_SLUG",0,u,"GetGprSeasons",0,d,"GetLeagueElo",0,o,"GetTeamGpr",0,a,"GprSeason",0,i,"GprTeamTournamentResult",0,n,"LOL_END_OF_YEAR_MILESTONE_SLUG",0,l,"TeamGpr",0,s,"VAL_END_OF_YEAR_MILESTONE_SLUG",0,c,"getCurrentYearForGpr",0,h,"getEarliestSupportedYearForGpr",0,function(e){switch(e){case r.Sport.Lol:return 2024;case r.Sport.Val:return 2025;default:throw Error("Unsupported sport")}},"getEndOfYearMilestoneSlug",0,v,"getFullTournamentName",0,function(e,t){if(!e)return t;let r=e.toLowerCase().split(/\s+/);return t.toLowerCase().split(/\s+/).some(e=>r.includes(e))?e:`${t} ${e}`},"getHistoryStartDate",0,function(e){return e?g(new Date(Date.UTC(parseInt(e),0,1))):g(new Date(Date.UTC(h(),0,1)))},"getISODateString",0,g,"getMilestonesForYear",0,function(e,t,a){if(a===r.Sport.Lol&&"2024"===e)return m;if(a===r.Sport.Val&&"2025"===e){let e=new Date;e.setUTCHours(23,59,0,0);let t=p.filter(t=>new Date(t.date)<=e);return new Date(p[0].date)>e&&t.push({date:g(e),slug:u,key:"current"}),t}let s=new Date;s.setUTCHours(23,59,0,0);let n=f(e,t,a),o=a===r.Sport.Lol?"gpr.endOfSplit":"gpr.endOfStage",i=n?.splits??[],l=i[i.length-1].endTime,c=i.filter(e=>new Date(e.endTime)<=s).map(e=>({date:g(new Date(e.endTime)),slug:e.endTime===l?v(a):e.slug.replace(/_/g,"-"),key:o,params:{splitName:e.name??"",stageName:e.name??""}})).sort((e,t)=>Date.parse(t.date)-Date.parse(e.date));return s<new Date(l)&&c.unshift({date:g(s),slug:u,key:"current"}),c},"getRankingsReleaseInfo",0,function(e,t,r=h().toString()){let a,s,n=h(),o=new Date,i=parseInt(r);if(i<n)return{areRankingsAvailable:!0,rankingsReleaseDate:new Date(Date.UTC(i,1,1,0,0,0))};let l=(a=f(h().toString(),e,t),s=a?.splits?.slice().sort((e,t)=>new Date(e.startTime).getTime()-new Date(t.startTime).getTime()),s?.[0]),c=l?.endTime?new Date(l.endTime):o;return{areRankingsAvailable:o>=c,rankingsReleaseDate:c}},"isInternationalTournament",0,function(e){let t=e.tournament.league.regionSlug?.toLowerCase()??"";return"global"===t||"intl"===t}])},84555,e=>{"use strict";var t=e.i(327126),r=e.i(292746),a=e.i(842157),s=e.i(92938),n=e.i(288842),o=e.i(562882),i=e.i(997e3),l=e.i(189108),c=e.i(808639),u=e.i(939013),d=e.i(503673),m=e.i(278849),p=e.i(795425),h=e.i(689718),f=e.i(412761),g=e.i(404398);e.i(235686);var v=e.i(465414),y=e.i(616557),w=e.i(693408);e.i(541354);var S=e.i(251084);let b=(0,S.sva)({slots:["container","header","heading","sponsor","sponsorImage","rows","footer","link","linkIcon"],base:{container:{display:"flex",flexDir:"column"},header:{display:"flex",flexDir:"column",gap:6,py:16},heading:{color:"unifiedText.primary",textStyle:"title/sm"},sponsor:{justifySelf:"center",color:"text.primary",h:20,w:"auto"},sponsorImage:{h:"inherit",w:"inherit"},rows:{display:"flex",flexDir:"column","& > *":{_before:{content:'""',position:"absolute",top:0,left:0,w:"100%",borderTop:"1px solid {colors.stroke.border.primary}"}},"& > :last-child":{_after:{content:'""',position:"absolute",bottom:0,left:0,w:"100%",borderTop:"1px solid {colors.stroke.border.primary}"}}},footer:{p:"12px 8px"},link:{display:"flex",justifyContent:"space-between",alignItems:"center",color:"unifiedText.brand",textStyle:"body/md"},linkIcon:{h:20,w:20,transform:"rotate(180deg)"}}})();function x(){let e,s,i,h,S,x,T,C,D,E,R,I,P,L,$,M=(0,r.c)(29),{track:N}=(0,g.useAnalytics)(),H=(0,w.useLocale)(),O=(0,n.useSport)();M[0]!==N?(e=()=>{N(f.AnalyticsEventTypes.GprPreviewWidgetNavigation)},M[0]=N,M[1]=e):e=M[1];let q=e;M[2]!==H||M[3]!==O?(s={hl:H,sport:O},M[2]=H,M[3]=O,M[4]=s):s=M[4],M[5]===Symbol.for("react.memo_cache_sentinel")?(i={fetchOptions:{next:{revalidate:600}}},M[5]=i):i=M[5],M[6]!==s?(h={variables:s,context:i},M[6]=s,M[7]=h):h=M[7];let{data:G}=(0,o.useSuspenseQuery)(p.GetGprSeasons,h);M[8]!==G.seasons?(S=(0,v.getFragmentData)(p.GprSeason,G.seasons),M[8]=G.seasons,M[9]=S):S=M[9];let F=S;M[10]!==F||M[11]!==O?(x=(0,p.getRankingsReleaseInfo)(F,O),M[10]=F,M[11]=O,M[12]=x):x=M[12];let{areRankingsAvailable:z,rankingsReleaseDate:A}=x,[B,U]=(0,a.useState)(!z);M[13]===Symbol.for("react.memo_cache_sentinel")?(T=new Date().getFullYear(),M[13]=T):T=M[13];let V=T;M[14]===Symbol.for("react.memo_cache_sentinel")?(C={key:"gpr.viewYear",vars:{year:V-1}},M[14]=C):C=M[14];let[W,Y]=(0,y.useTranslations)("gpr.viewFullRankings",C);M[15]===Symbol.for("react.memo_cache_sentinel")?(D=()=>{U(!1)},M[15]=D):D=M[15];let Q=D;M[16]===Symbol.for("react.memo_cache_sentinel")?(E=(0,t.jsx)("span",{className:b.heading,children:m.gprProductName}),M[16]=E):E=M[16],M[17]===Symbol.for("react.memo_cache_sentinel")?(R=(0,t.jsxs)("div",{className:b.header,children:[E,(0,t.jsx)("div",{className:b.sponsor,children:(0,t.jsx)(u.default,{className:b.sponsorImage})})]}),M[17]=R):R=M[17],M[18]!==B||M[19]!==A?(I=(0,t.jsx)("div",{className:b.rows,children:B?(0,t.jsx)(a.Suspense,{fallback:(0,t.jsx)(j,{}),children:(0,t.jsx)(d.GprCountdownWidget,{endDate:A.toISOString(),variants:{size:"small"},onDone:Q})}):(0,t.jsx)(a.Suspense,{fallback:(0,t.jsx)(_,{}),children:(0,t.jsx)(k,{})})}),M[18]=B,M[19]=A,M[20]=I):I=M[20];let K=`/${H}/gpr`,X=B?Y:W;return M[21]===Symbol.for("react.memo_cache_sentinel")?(P=(0,t.jsx)(c.default,{className:b.linkIcon}),M[21]=P):P=M[21],M[22]!==q||M[23]!==K||M[24]!==X?(L=(0,t.jsx)("div",{className:b.footer,children:(0,t.jsxs)(l.default,{className:b.link,href:K,onClick:q,prefetch:!1,children:[X,P]})}),M[22]=q,M[23]=K,M[24]=X,M[25]=L):L=M[25],M[26]!==I||M[27]!==L?($=(0,t.jsxs)("div",{className:b.container,children:[R,I,L]}),M[26]=I,M[27]=L,M[28]=$):$=M[28],$}let T=(0,S.sva)({slots:["row","rank","team","teamCode","imageContainer","image"],base:{row:{pos:"relative",display:"flex",justifyContent:"start",alignItems:"center",p:"12px 8px"},rank:{color:"unifiedText.primary",textStyle:"title/md",w:36},team:{display:"flex",justifyContent:"start",alignItems:"center",gap:8},teamCode:{color:"unifiedText.primary",textStyle:"title/sm"},imageContainer:{pos:"relative",h:32,aspectRatio:"1:1"},image:{objectFit:"contain",objectPosition:"center"}}})();function k(){let e,a,s,i,l,c,u,d,h=(0,r.c)(14),f=(0,w.useLocale)(),g=(0,n.useSport)();h[0]===Symbol.for("react.memo_cache_sentinel")?(e=(0,p.getHistoryStartDate)(),h[0]=e):e=h[0];let y=e;h[1]===Symbol.for("react.memo_cache_sentinel")?(a=(0,p.getISODateString)(new Date),h[1]=a):a=h[1];let S=a;h[2]!==f||h[3]!==g?(s={hl:f,step:m.gprHistoryStep,startDate:y,endDate:S,sport:g},h[2]=f,h[3]=g,h[4]=s):s=h[4],h[5]===Symbol.for("react.memo_cache_sentinel")?(i={fetchOptions:{next:{revalidate:600}}},h[5]=i):i=h[5],h[6]!==s?(l={variables:s,context:i},h[6]=s,h[7]=l):l=h[7];let{data:b}=(0,o.useSuspenseQuery)(p.GetTeamGpr,l);h[8]!==b.teamGPR?(c=[...(0,v.getFragmentData)(p.TeamGpr,b.teamGPR)].sort(D).slice(0,3),h[8]=b.teamGPR,h[9]=c):c=h[9];let x=c;return h[10]!==x?(u=x.map(C),h[10]=x,h[11]=u):u=h[11],h[12]!==u?(d=(0,t.jsx)(t.Fragment,{children:u}),h[12]=u,h[13]=d):d=h[13],d}function C(e){return(0,t.jsxs)(i.motion.div,{layout:!0,className:T.row,initial:{opacity:0,scaleY:0},animate:{opacity:1,scaleY:1},transition:{duration:.3,ease:"easeInOut"},children:[(0,t.jsx)("span",{className:T.rank,children:e.currentTeamGPR.rank}),(0,t.jsxs)("div",{className:T.team,children:[(0,t.jsx)("div",{className:T.imageContainer,children:(0,t.jsx)(h.Image,{fill:!0,alt:"",className:T.image,sizes:"48px",src:e.team.image??""})}),(0,t.jsx)("span",{className:T.teamCode,children:e.team.code})]})]},e.id)}function D(e,t){return e.currentTeamGPR.rank-t.currentTeamGPR.rank}let E=(0,S.sva)({slots:["container","content","gradient"],base:{container:{pos:"relative",display:"flex",justifyContent:"start",alignItems:"center",p:"12px 8px"},content:{h:32,w:"100%"},gradient:{h:"100%",w:"100%",bg:"linear-gradient(90deg, {colors.gray.102/30} 15%, {colors.gray.101/30} 50%, {colors.neutral.white/30} 65%, {colors.gray.101/30} 75%, {colors.gray.511/30} 100%)",borderRadius:4,backgroundSize:"200% 100%",animation:"backgroundSwipe 1.5s linear infinite"}},variants:{type:{teams:{content:{h:32,w:"100%"}},countdown:{content:{h:87,w:"100%"}}}}}),R=E({type:"countdown"}),I=E({type:"teams"}),j=(0,a.memo)(function(){let e,a=(0,r.c)(1);return a[0]===Symbol.for("react.memo_cache_sentinel")?(e=(0,t.jsx)("div",{className:R.container,children:(0,t.jsx)("div",{className:R.content,children:(0,t.jsx)("div",{className:R.gradient})})}),a[0]=e):e=a[0],e}),_=(0,a.memo)(function(){return Array.from({length:3}).map((e,r)=>(0,t.jsx)("div",{className:I.container,children:(0,t.jsx)("div",{className:I.content,children:(0,t.jsx)("div",{className:I.gradient})})},r))});e.s(["GprPreviewWidget",0,function(){let e,o=(0,r.c)(2),i=(0,n.useSport)();if(i!==s.Sport.Lol&&i!==s.Sport.Val){let e;return o[0]===Symbol.for("react.memo_cache_sentinel")?(e=(0,t.jsx)(t.Fragment,{}),o[0]=e):e=o[0],e}return o[1]===Symbol.for("react.memo_cache_sentinel")?(e=(0,t.jsx)(a.Suspense,{fallback:(0,t.jsx)("div",{}),children:(0,t.jsx)(x,{})}),o[1]=e):e=o[1],e},"generateStaticParams",0,function(){return[]},"revalidate",0,30],84555)},64568,e=>{"use strict";var t=e.i(292746),r=e.i(699627),a=e.i(842157);e.i(989837);var s=e.i(151044),n=e.i(616557),o=e.i(975157),i=e.i(748203),l=e.i(93015);function c(e){let r,s=(0,t.c)(2),n=void 0===e?"home[scroll]":e,i=(0,a.useRef)(null);return s[0]!==n?(r=()=>{if(!(0,o.isSSR)())if(i.current)return i.current;else return i.current=document.getElementById(n)},s[0]=n,s[1]=r):r=s[1],r}let u={today:"section[data-today=target]",default:"section[data-scroll=target]"},d={today:void 0,default:void 0};function m(e){let s,n,o=(0,t.c)(4),i=void 0===e?"default":e,l=(0,r.useParams)();return o[0]!==l?(s=[l],o[0]=l,o[1]=s):s=o[1],(0,a.useEffect)(p,s),o[2]!==i?(n=()=>{let e=d[i];return e?.length?e:d[i]=document.querySelectorAll(u[i])},o[2]=i,o[3]=n):n=o[3],n}function p(){d={today:void 0,default:void 0}}e.s(["clearCacheScrollElements",0,function(){d={today:void 0,default:void 0}},"useDateParts",0,function(e){let r,a,o=(0,t.c)(7);o[0]!==e?(r=Date.parse(e),o[0]=e,o[1]=r):r=o[1];let i=r,l=(0,n.useFormatDate)(i,"RelativeWeekday"),c=(0,n.useFormatDate)(i,"ShortDayMonth"),u=(0,n.useFormatDate)(i,"ShortDayMonthYear"),d=(0,s.dayjs)().startOf("day").utc().isSame(i,"year")?c:u;return o[2]!==d||o[3]!==c||o[4]!==u||o[5]!==l?(a={date:d,weekday:l,shortDayMonth:c,shortDayMonthAndYear:u},o[2]=d,o[3]=c,o[4]=u,o[5]=l,o[6]=a):a=o[6],a},"useGetScollWindow",0,c,"useGetScrollableElements",0,m,"useScrollSnapToToday",0,function(){let e,s,n,o=(0,t.c)(14),{past:u,present:d,future:p}=(0,l.useHome)(),h=!u||!d||!p,{scrollOffset:f}=(0,i.useHomeScroll)(),g=(0,i.useHomeScrollUpdater)(),v=(0,a.useRef)(void 0),y=(0,a.useRef)(0),w=m(),S=m("today"),b=c();o[0]!==w||o[1]!==b||o[2]!==S||o[3]!==f||o[4]!==g?(e=()=>{let e,t=b(),r=S(),a=r[0];if(!t||!r.length||!a)return;t.scrollTo({top:r[0].offsetTop-f-12,behavior:"instant"});let s=w();for(let t=0;t<s.length;t++)if(s[t]===r[0]){e=t;break}g({type:"scroll",payload:{ref:"snap",scrollIndex:e,scrollTargetIndex:e,scrollDate:r[0].dataset.date,scrollWeekday:r[0].dataset.weekday,scrollBehavior:"smooth",scrollIsToday:!0}}),window.clearInterval(v.current),y.current=0},o[0]=w,o[1]=b,o[2]=S,o[3]=f,o[4]=g,o[5]=e):e=o[5];let x=e,T=(0,r.useParams)();o[6]!==h||o[7]!==x?(s=()=>{let e=v.current;return y.current=0,window.clearInterval(e),h||(v.current=window.setInterval(()=>{if(y.current>25){window.clearInterval(v.current),y.current=0;return}x(),y.current=y.current+1},50)),()=>{window.clearInterval(e),y.current=0}},o[6]=h,o[7]=x,o[8]=s):s=o[8],o[9]!==T||o[10]!==h||o[11]!==x||o[12]!==g?(n=[g,x,T,h],o[9]=T,o[10]=h,o[11]=x,o[12]=g,o[13]=n):n=o[13],(0,a.useLayoutEffect)(s,n)}])},246446,e=>{"use strict";var t=e.i(126476);e.i(235686);var r=e.i(710553);let a=(0,t.buildCookieName)("essential","filter","home-leagues-filter"),s=(0,r.graphql)(`
  query homeLeagues($hl: Locale!, $sport: [Sport], $flags: [LeagueFlags]) {
    leagues(hl: $hl, sport: $sport, flags: $flags) {
      ...HomeLeague
    }
  }
`),n=(0,r.graphql)(`
  fragment HomeLeague on League {
    id
    name
    slug
    region
    image
    displayPriority {
      position
      status
    }
  }
`),o=(0,r.graphql)(`
  query homeEvents(
    $hl: Locale!
    $sport: [Sport]
    $leagues: [ID]
    $tournamentIds: [ID]
    $eventDateStart: Date
    $eventDateEnd: Date
    $eventState: [EventState]
    $eventType: EventType
    $pageSize: Int
    $vodType: [VodType]
    $pageToken: Token
  ) {
    esports(
      hl: $hl
      sport: $sport
      leagueId: $leagues
      tournamentId: $tournamentIds
      eventDateStart: $eventDateStart
      eventDateEnd: $eventDateEnd
      eventState: $eventState
      eventType: $eventType
      pageSize: $pageSize
      pageToken: $pageToken
    ) {
      events {
        ...HomeEventMatch
        ...HomeEventShow
      }
      pages {
        older
        newer
      }
    }
  }
`),i=(0,r.graphql)(`
  fragment HomeEventMatch on EventMatch {
    id
    blockName
    startTime
    state
    type
    league {
      id
      name
      image
      slug
      displayPriority {
        status
        position
      }
    }
    tournament {
      id
      name
      state
    }
    matchTeams {
      id
      teamId
      homeLeague {
        image
        regionSlug
      }
      name
      image
      lightImage
      code
      result {
        gameWins
        outcome
      }
    }
    match {
      id
      state
      flags
      type
      strategy {
        type
        count
      }
      games {
        id
        state
        number
        vods {
          ...WatchVodVod
          id
          parameter
          startMillis
          endMillis
        }
        recaps: vods(type: $vodType) {
          id
          parameter
          startMillis
          endMillis
        }
      }
    }
    streams {
      id
      parameter
      provider
      countries
      offset
      mediaLocale {
        locale
        englishName
        translatedName
      }
    }
  }
`),l=(0,r.graphql)(`
  fragment HomeEventShow on EventShow {
    id
    startTime
    state
    type
    league {
      id
      name
      image
      slug
      displayPriority {
        status
        position
      }
    }
    tournament {
      id
      name
    }
    streams {
      id
      parameter
      provider
      countries
      offset
      mediaLocale {
        locale
        englishName
        translatedName
      }
    }
  }
`);(0,r.graphql)(`
  query lolHomepageWidgets(
    $where: LolEsportsHomepageMultisiteFilter
    $fallbackWhere: LolEsportsHomepageMultisiteFilter
  ) {
    widgets: allLolEsportsHomepageMultisite(where: $where) {
      _updatedAt
      language
      title
      seasonTopImageDefault {
        asset {
          url
        }
      }
      seasonHeaderImage {
        asset {
          url
        }
      }
      seasonEventList {
        ...HomeSeasonEvent
      }
    }
    fallback: allLolEsportsHomepageMultisite(where: $fallbackWhere) {
      _updatedAt
      language
      title
      seasonTopImageDefault {
        asset {
          url
        }
      }
      seasonHeaderImage {
        asset {
          url
        }
      }
      seasonEventList {
        ...HomeSeasonEvent
      }
    }
  }
`),(0,r.graphql)(`
  query valHomepageWidgets(
    $where: ValEsportsHomepageMultisiteFilter
    $fallbackWhere: ValEsportsHomepageMultisiteFilter
  ) {
    widgets: allValEsportsHomepageMultisite(where: $where) {
      _updatedAt
      language
      title
      seasonTopImageDefault {
        asset {
          url
        }
      }
      seasonHeaderImage {
        asset {
          url
        }
      }
      seasonEventList {
        ...HomeSeasonEvent
      }
    }
    fallback: allValEsportsHomepageMultisite(where: $fallbackWhere) {
      _updatedAt
      language
      title
      seasonTopImageDefault {
        asset {
          url
        }
      }
      seasonHeaderImage {
        asset {
          url
        }
      }
      seasonEventList {
        ...HomeSeasonEvent
      }
    }
  }
`),(0,r.graphql)(`
  fragment HomeSeasonEvent on EsportsSeasonEvent {
    seasonDateFormat
    seasonDateStart
    seasonDateEnd
    seasonEyebrown
    seasonTitle
    seasonTopImage {
      asset {
        url
      }
    }
  }
`),e.s(["HomeEventMatch",0,i,"HomeEventShow",0,l,"HomeEvents",0,o,"HomeLeague",0,n,"HomeLeagues",0,s,"filterCookieName",0,a,"safeDecodeURIComponent",0,function(e){if(e)try{return decodeURIComponent(e)}catch{return}}])},133864,e=>{"use strict";var t=e.i(327126),r=e.i(292746),a=e.i(915279),s=e.i(616557);function n(e){let a,n=(0,r.c)(3),{resetErrorBoundary:o}=e,i=(0,s.useTranslations)("action.tryAgain");return n[0]!==o||n[1]!==i?(a=(0,t.jsx)("div",{children:(0,t.jsx)("button",{onClick:o,children:i})}),n[0]=o,n[1]=i,n[2]=a):a=n[2],a}e.s(["HomeErrorBoundary",0,function(e){let s,o=(0,r.c)(2),{children:i}=e;return o[0]!==i?(s=(0,t.jsx)(a.ErrorBoundary,{FallbackComponent:n,children:i}),o[0]=i,o[1]=s):s=o[1],s}])},748203,e=>{"use strict";let t;var r=e.i(327126),a=e.i(292746),s=e.i(842157),n=e.i(975157);let o={scrollIndex:0,scrollTargetIndex:0,scrollOffset:0,scrollWeekday:"",scrollDate:"",scrollIsToday:!1,scrollBehavior:"smooth",passive:!0},i=(0,s.createContext)(o),l=(0,s.createContext)(()=>void 0),c=(e,t)=>{switch(t.type){case"scrollPrev":return{...e,scrollTargetIndex:Math.max(0,e.scrollTargetIndex<e.scrollIndex?e.scrollTargetIndex-1:e.scrollIndex-1),passive:!1};case"scrollNext":{let r=t.payload.max;return{...e,scrollTargetIndex:Math.min(e.scrollTargetIndex>e.scrollIndex?e.scrollTargetIndex+1:e.scrollIndex+1,r),passive:!1}}case"scroll":{let r=t.payload;return{...e,scrollIndex:r?.scrollIndex??e.scrollIndex,scrollTargetIndex:r?.scrollTargetIndex??e.scrollTargetIndex,scrollOffset:r?.scrollOffset??e.scrollOffset,scrollWeekday:r?.scrollWeekday??e.scrollWeekday,scrollDate:r?.scrollDate??e.scrollDate,scrollIsToday:r?.scrollIsToday??e.scrollIsToday,scrollBehavior:r?.scrollBehavior??e.scrollBehavior,passive:r?.passive??e.passive}}default:return e}};function u(){return(0,s.use)(l)}e.s(["HomeScrollProvider",0,function(e){let t,n,u=(0,a.c)(5),{children:d}=e,[m,p]=(0,s.useReducer)(c,o);return u[0]!==d?(t=(0,r.jsx)(l.Provider,{value:p,children:d}),u[0]=d,u[1]=t):t=u[1],u[2]!==m||u[3]!==t?(n=(0,r.jsx)(i.Provider,{value:m,children:t}),u[2]=m,u[3]=t,u[4]=n):n=u[4],n},"useHomeScroll",0,function(){return(0,s.use)(i)},"useHomeScrollDebouncedUpdater",0,function(e){let r,o,i,l=(0,a.c)(5),c=void 0===e?100:e,d=u(),m=(0,s.useRef)(void 0);return l[0]!==c?(r=()=>{t=e=>{(0,n.isSSR)()||(window.clearTimeout(m.current),m.current=window.setTimeout(()=>{e()},c))}},o=[c],l[0]=c,l[1]=r,l[2]=o):(r=l[1],o=l[2]),(0,s.useEffect)(r,o),l[3]!==d?(i=e=>{t(()=>{d(e)})},l[3]=d,l[4]=i):i=l[4],i},"useHomeScrollUpdater",0,u])},93015,e=>{"use strict";var t=e.i(327126),r=e.i(292746),a=e.i(842157),s=e.i(493690),n=e.i(975157);let o={past:!1,present:!1,future:!1,spoiler:!0},i=(0,a.createContext)(o),l=(0,a.createContext)(()=>void 0),c=(e,t)=>{switch(t.type){case"toggle-spoiler":return(0,n.isSSR)()||(0,s.setLocalStorageValue)("spoiler-protection",!e.spoiler),{...e,spoiler:!e.spoiler};case"set":if(t.payload)return{...e,...t.payload};return e;default:return e}};e.s(["HomeStateProvider",0,function(e){let u,d,m,p,h=(0,r.c)(7),{children:f}=e,[g,v]=(0,a.useReducer)(c,o);return h[0]===Symbol.for("react.memo_cache_sentinel")?(u=()=>{v({type:"set",payload:{spoiler:(0,n.isSSR)()?o.spoiler:(0,s.getLocalStorageValue)("spoiler-protection")??o.spoiler}})},d=[],h[0]=u,h[1]=d):(u=h[0],d=h[1]),(0,a.useEffect)(u,d),h[2]!==f?(m=(0,t.jsx)(l.Provider,{value:v,children:f}),h[2]=f,h[3]=m):m=h[3],h[4]!==g||h[5]!==m?(p=(0,t.jsx)(i.Provider,{value:g,children:m}),h[4]=g,h[5]=m,h[6]=p):p=h[6],p},"useHome",0,function(){return(0,a.use)(i)},"useHomeUpdater",0,function(){return(0,a.use)(l)}])},473483,e=>{"use strict";var t=e.i(327126),r=e.i(292746),a=e.i(685149);e.i(989837);var s=e.i(151044),n=e.i(693408),o=e.i(288842);function i(e,r){return(0,t.jsx)(u,{title:e.title,subtitle:e.subtitle,start:e.start,end:e.end,type:e.type,active:e.active},`season-event-${e.start}-${e.end}:${r}`)}function l(e,t){return e?.seasonDateStart&&t?.seasonDateStart?e.seasonDateStart<t.seasonDateStart?-1:+(e.seasonDateStart>t.seasonDateStart):0}e.i(541354);let c=(0,e.i(251084).sva)({slots:["event","title","subtitle","timeframe","active"],base:{event:{pos:"relative",display:"flex",flexDir:"column",justifyContent:"center",alignItems:"start",gap:4,w:"100%",h:"100%",px:16,py:8,zIndex:"zLayer",color:"text.primary"},title:{textStyle:"title/md",lineHeight:"100%"},subtitle:{textTransform:"capitalize",textStyle:"label/lg",lineHeight:"100%"},timeframe:{textStyle:"body/md",lineHeight:"100%"},active:{pos:"absolute",inset:0,zIndex:"zBelow",borderLeft:"2px solid {colors.home.seasonOverview.accentText}"}},variants:{state:{completed:{event:{opacity:.5},title:{color:"home.seasonOverview.completedText"},subtitle:{color:"home.seasonOverview.completedText"},timeframe:{color:"home.seasonOverview.completedText"}},inProgress:{title:{color:"home.seasonOverview.accentText"},subtitle:{color:"home.seasonOverview.subtitleText"},timeframe:{color:"home.seasonOverview.subtitleText"}},unstarted:{title:{color:"home.seasonOverview.titleText"},subtitle:{color:"home.seasonOverview.subtitleText"},timeframe:{color:"home.seasonOverview.subtitleText"}}},sport:{lol:{active:{bg:"linear-gradient(90deg, rgba(16, 228, 249, 0.2) 40.5%, {colors.home.seasonOverview.accentText/1} 100%)"}},val:{active:{bg:"linear-gradient(90deg, rgba(220, 48, 48, 0.2) 49.5%, {colors.home.seasonOverview.accentText/1} 100%)"}},tft:{},rb:{},wr:{}}},compoundVariants:[]});function u(e){var i,l,u;let m,p,h,f=(0,r.c)(45),{title:g,subtitle:v,start:y,end:w,type:S,active:b}=e,x=(0,o.useSport)(),T=(0,n.useLocale)();f[0]!==b||f[1]!==w||f[2]!==x||f[3]!==y?(p=c({sport:x,state:(i=y,l=w,u=b,m=(0,s.dayjs)().startOf("day").utc(),u||m.isBetween(i,l??i)?"inProgress":m.isAfter(l??i)?"completed":"unstarted")}),f[0]=b,f[1]=w,f[2]=x,f[3]=y,f[4]=p):p=f[4];let k=p;if(f[5]!==b||f[6]!==k||f[7]!==w||f[8]!==T||f[9]!==y||f[10]!==v||f[11]!==g||f[12]!==S){h=Symbol.for("react.early_return_sentinel");e:{let e=y?new Date(y):"",r=w?new Date(w):"";switch(S){case"day":{let s,n,o,i=d(T,S),l=e?i.format(e):void 0,c=r?i.format(r):void 0;f[14]!==b||f[15]!==k.active?(s=b&&(0,t.jsx)("div",{className:k.active}),f[14]=b,f[15]=k.active,f[16]=s):s=f[16],f[17]!==k.subtitle||f[18]!==v?(n=(0,t.jsx)("span",{className:k.subtitle,children:v}),f[17]=k.subtitle,f[18]=v,f[19]=n):n=f[19],f[20]!==k.title||f[21]!==g?(o=(0,t.jsx)("span",{className:k.title,children:g}),f[20]=k.title,f[21]=g,f[22]=o):o=f[22],h=(0,t.jsxs)("div",{className:k.event,children:[s,n,o,(0,t.jsxs)("span",{className:k.timeframe,children:[l??"",l&&c?`${a.Chars.Space}${a.Chars.Dash}${a.Chars.Space}`:"",c??""]})]});break e}case"month":{let s,n,o,i,l,c=d(T,S,w?"short":"long"),u=e?c.format(e):void 0,m=r?c.format(r):void 0;f[23]!==b||f[24]!==k.active?(s=b&&(0,t.jsx)("div",{className:k.active}),f[23]=b,f[24]=k.active,f[25]=s):s=f[25],f[26]!==k.subtitle||f[27]!==v?(n=(0,t.jsx)("span",{className:k.subtitle,children:v}),f[26]=k.subtitle,f[27]=v,f[28]=n):n=f[28],f[29]!==k.title||f[30]!==g?(o=(0,t.jsx)("span",{className:k.title,children:g}),f[29]=k.title,f[30]=g,f[31]=o):o=f[31];let p=u??"",y=u&&m?`${a.Chars.Space}${a.Chars.Dash}${a.Chars.Space}`:"",x=m??"";f[32]!==k.timeframe||f[33]!==p||f[34]!==y||f[35]!==x?(i=(0,t.jsxs)("span",{className:k.timeframe,children:[p,y,x]}),f[32]=k.timeframe,f[33]=p,f[34]=y,f[35]=x,f[36]=i):i=f[36],f[37]!==b||f[38]!==k.event||f[39]!==s||f[40]!==n||f[41]!==o||f[42]!==i?(l=(0,t.jsxs)("div",{className:k.event,"data-active":b,children:[s,n,o,i]}),f[37]=b,f[38]=k.event,f[39]=s,f[40]=n,f[41]=o,f[42]=i,f[43]=l):l=f[43],h=l;break e}default:{let e;f[44]===Symbol.for("react.memo_cache_sentinel")?(e=(0,t.jsx)(t.Fragment,{}),f[44]=e):e=f[44],h=e;break e}}}f[5]=b,f[6]=k,f[7]=w,f[8]=T,f[9]=y,f[10]=v,f[11]=g,f[12]=S,f[13]=h}else h=f[13];if(h!==Symbol.for("react.early_return_sentinel"))return h}function d(e,t,r){let a={monthLong:new Intl.DateTimeFormat(e,{month:"long"}),monthShort:new Intl.DateTimeFormat(e,{month:"short"}),day:new Intl.DateTimeFormat(e,{month:"short",day:"numeric"})};return"month"!==t?a[t]:"short"===r?a.monthShort:a.monthLong}e.s(["HomeSeasonEvents",0,function(e){let a,n,o=(0,r.c)(5),{events:c}=e;e:{let e;if(!c?.length){let e;o[0]===Symbol.for("react.memo_cache_sentinel")?(e=[],o[0]=e):e=o[0],a=e;break e}if(o[1]!==c){for(let t of(e=[],c.sort(l))){if(!t)continue;let r=t.seasonDateStart?(0,s.dayjs)(t.seasonDateStart).startOf("day").utc().toISOString():void 0,a=t.seasonDateEnd?(0,s.dayjs)(t.seasonDateEnd).startOf("day").utc().toISOString():void 0;e.push({title:t.seasonTitle??"",subtitle:t.seasonEyebrown??"",start:r,end:a,type:t.seasonDateFormat?.includes("day")?"day":"month",active:function(e,t){let r=new Date().toISOString();return e&&t?r>=e&&r<=t:!!e&&new Date().getMonth()===new Date(e).getMonth()}(r,a)})}o[1]=c,o[2]=e}else e=o[2];a=e}let u=a;return o[3]!==u?(n=(0,t.jsx)(t.Fragment,{children:u.map(i)}),o[3]=u,o[4]=n):n=o[4],n}],473483)},447642,e=>{"use strict";var t=e.i(327126),r=e.i(292746),a=e.i(961341),s=e.i(997e3),n=e.i(189108),o=e.i(842157),i=e.i(689718),l=e.i(412761),c=e.i(404398),u=e.i(685149),d=e.i(616557);e.i(541354);let m=(0,e.i(251084).sva)({slots:["image","link"],base:{link:{pos:"absolute",top:0,left:0,display:"block",w:"100%",h:"auto"},image:{display:"block",w:"100%",h:"auto",overflow:"hidden",borderRadius:4}}})(),p=6*u.Times.Second;e.s(["SponsorCarousel",0,function(e){let u,h,f,g,v,y,w=(0,r.c)(20),{sponsors:S}=e,b=(0,d.useTranslation)("sponsor"),[x,T]=(0,o.useState)(0);w[0]!==x||w[1]!==S?(u=()=>{S?.length&&(x===S.length-1?T(0):T(x+1))},w[0]=x,w[1]=S,w[2]=u):u=w[2];let k=u,{track:C}=(0,c.useAnalytics)();w[3]!==x||w[4]!==S||w[5]!==C?(h=()=>{C(l.AnalyticsEventTypes.HomeSponsorClicked,{type:"click",value:S?.[x]?.sponsorUrl??""})},w[3]=x,w[4]=S,w[5]=C,w[6]=h):h=w[6];let D=h,E=(0,o.useRef)(void 0);return w[7]!==k||w[8]!==S?.length?(f=()=>{if(S?.length)return E.current=window.setInterval(k,p),()=>{window.clearInterval(E.current)}},w[7]=k,w[8]=S?.length,w[9]=f):f=w[9],w[10]!==k||w[11]!==S?(g=[S,k],w[10]=k,w[11]=S,w[12]=g):g=w[12],(0,o.useEffect)(f,g),w[13]!==x||w[14]!==D||w[15]!==b||w[16]!==S?(v=S?.map((e,r)=>r===x&&(0,t.jsx)(s.motion.div,{animate:{opacity:1},exit:{opacity:0},initial:{opacity:0},children:(0,t.jsx)(n.default,{"aria-label":b||"sponsor",className:m.link,prefetch:!1,href:e?.sponsorUrl??"",target:"_blank",onClick:D,children:(0,t.jsx)(i.Image,{className:m.image,src:e?.sponsorImage?.asset?.url??"",width:-1,height:-1,sizes:"269px",alt:""})})},`${e?.sponsorUrl}-${r}`)),w[13]=x,w[14]=D,w[15]=b,w[16]=S,w[17]=v):v=w[17],w[18]!==v?(y=(0,t.jsx)(a.AnimatePresence,{children:v}),w[18]=v,w[19]=y):y=w[19],y}])},208265,e=>{"use strict";var t=e.i(327126),r=e.i(292746);let a=(0,e.i(465040).default)(()=>e.A(378174).then(e=>e.PickemsCTABannerComponent),{loadableGenerated:{modules:[101503]},ssr:!1});e.s(["PickemsCTABanner",0,function(){let e,s=(0,r.c)(1);return s[0]===Symbol.for("react.memo_cache_sentinel")?(e=(0,t.jsx)(a,{}),s[0]=e):e=s[0],e}])},108101,e=>{"use strict";var t=e.i(327126),r=e.i(292746),a=e.i(64568),s=e.i(748203),n=e.i(415129),o=e.i(92938),i=e.i(616557),l=e.i(693408),c=e.i(775480),u=e.i(684496);e.i(541354);var d=e.i(251084);let m=(0,c.createLogger)("schedule.util"),p=(0,d.sva)({slots:["time","ampm"],base:{time:{alignItems:"center",color:"unifiedText.primary",display:"flex",gap:50,textStyle:"title/sm"},ampm:{color:"unifiedText.secondary",textStyle:"label/md"}}})();e.s(["SeasonType",0,function(e){let{tournamentType:t}=e,[r,a]=(0,i.useTranslations)("pathToPro","proCircuit");switch(t){case n.TftTournamentType.ProCircuit:return a;case n.TftTournamentType.TacticiansCup:case n.TftTournamentType.RegionalFinals:case n.TftTournamentType.TacticiansTrials:return r;case n.TftTournamentType.TacticiansCrown:return"";default:return m.error("Unknown tournament type."),""}},"Time",0,function(e){let a,s,n,o=(0,r.c)(9),{dateTime:i}=e,c=(0,l.useLocale)();o[0]!==i||o[1]!==c?(a=(0,u.getTimeParts)(i,c),o[0]=i,o[1]=c,o[2]=a):a=o[2];let{hour:d,literal:m,minute:h,ampm:f}=a,g=`${d}${m}${h}`;return o[3]!==f?(s=f?(0,t.jsx)("span",{className:p.ampm,children:f}):(0,t.jsx)(t.Fragment,{}),o[3]=f,o[4]=s):s=o[4],o[5]!==i||o[6]!==s||o[7]!==g?(n=(0,t.jsxs)("time",{className:p.time,dateTime:i,children:[g,s]}),o[5]=i,o[6]=s,o[7]=g,o[8]=n):n=o[8],n},"useEventOptions",0,function(){return[{label:"Pro Circuit",value:o.CompeteTournamentType.ProCircuit},{label:"Tactician's Trials",value:o.CompeteTournamentType.TacticiansTrials},{label:"Regional Finals",value:o.CompeteTournamentType.RegionalFinals},{label:"Tactician's Crown",value:o.CompeteTournamentType.TacticiansCrown}]},"useMilestoneOptions",0,function(){let e,t,a,s,n,l=(0,r.c)(13),[c,u,d,m]=(0,i.useTranslations)("trialSnapshots","ladderPointSnapshots","registrationOpen","registrationClose"),p=c??"Trial Snapshots";return l[0]!==p?(e={label:p,value:o.CompeteScheduleMilestone.CupSnapshot},l[0]=p,l[1]=e):e=l[1],l[2]!==u?(t={label:u,value:o.CompeteScheduleMilestone.LadderPointSnapshot},l[2]=u,l[3]=t):t=l[3],l[4]!==d?(a={label:d,value:o.CompeteScheduleMilestone.RegistrationOpen},l[4]=d,l[5]=a):a=l[5],l[6]!==m?(s={label:m,value:o.CompeteScheduleMilestone.RegistrationClose},l[6]=m,l[7]=s):s=l[7],l[8]!==e||l[9]!==t||l[10]!==a||l[11]!==s?(n=[e,t,a,s],l[8]=e,l[9]=t,l[10]=a,l[11]=s,l[12]=n):n=l[12],n},"useRegionOptions",0,function(){let e,t,a,s,n,l=(0,r.c)(13),[c,u,d,m]=(0,i.useTranslations)("region.amer","region.apac","region.emea","region.cn");return l[0]!==c?(e={label:c,value:o.TftRegion.Amer},l[0]=c,l[1]=e):e=l[1],l[2]!==u?(t={label:u,value:o.TftRegion.Apac},l[2]=u,l[3]=t):t=l[3],l[4]!==d?(a={label:d,value:o.TftRegion.Emea},l[4]=d,l[5]=a):a=l[5],l[6]!==m?(s={label:m,value:o.TftRegion.Cn},l[6]=m,l[7]=s):s=l[7],l[8]!==e||l[9]!==t||l[10]!==a||l[11]!==s?(n=[e,t,a,s],l[8]=e,l[9]=t,l[10]=a,l[11]=s,l[12]=n):n=l[12],n},"useScheduleScrollToToday",0,function(){let e,t=(0,r.c)(4),n=(0,s.useHomeScrollUpdater)(),o=(0,a.useGetScrollableElements)("today"),i=(0,a.useGetScrollableElements)();return t[0]!==i||t[1]!==o||t[2]!==n?(e=()=>{let e=o(),t=Array.from(i()).findIndex(t=>t===e[0]);n({type:"scroll",payload:{ref:"today",scrollIndex:t,scrollTargetIndex:t,scrollWeekday:"",scrollIsToday:!0,scrollBehavior:"instant",passive:!1}})},t[0]=i,t[1]=o,t[2]=n,t[3]=e):e=t[3],e}])},623664,e=>{"use strict";var t,r=e.i(327126),a=e.i(292746),s=e.i(875275),n=e.i(112476),o=e.i(842157);function i(){return(i=Object.assign.bind()).apply(null,arguments)}let l=function(e){return o.createElement("svg",i({xmlns:"http://www.w3.org/2000/svg",width:12,height:12,fill:"none",viewBox:"0 0 12 12"},e),t||(t=o.createElement("path",{fill:"#000",fillRule:"evenodd",d:"M1.417 0 0 1.522l4.596 4.675-4.21 4.281L1.804 12l4.249-4.322 4.145 4.217 1.416-1.522-4.105-4.176L12 1.627 10.583.105l-4.531 4.61z",clipRule:"evenodd"})))};e.i(541354);var c=e.i(963336);let u=(0,e.i(251084).sva)({slots:["wrapper","switchRoot","switchThumb","label","checkedIcon","uncheckedIcon"],base:{wrapper:{display:"flex",alignItems:"center",gap:12},switchRoot:{w:40,h:24,backgroundColor:"surface.level.1",border:"2px solid {colors.stroke.rule}",borderRadius:20,position:"relative",cursor:"pointer",WebkitTapHighlightColor:"rgba(0, 0, 0, 0)",flexShrink:0,boxShadow:{_focus:{_hover:"0 0 0 2px {colors.surface.level.2}"}},'&[data-state="checked"]':{border:"0px",backgroundColor:"surface.brand","& .unchecked":{display:"none"},boxShadow:{_hover:{_focus:"0 0 0 2px {colors.stroke.rule}"}}},'&[data-state="unchecked"]':{"& .checked":{display:"none"}},lg:{w:50,h:30}},switchThumb:{display:"flex",justifyContent:"center",alignItems:"center",w:18,h:18,backgroundClip:"padding-box",border:"1px solid rgba(0,0,0, 0.15)",backgroundColor:"icon.primary",borderRadius:"full",transition:"transform 100ms",transform:"translateX(1px)",boxSizing:"content-box",willChange:"transform",'[data-state="checked"] &':{transform:"translateX(18px)"},lg:{w:24,h:24,'[data-state="checked"] &':{transform:"translateX(22px)"}}},label:{color:"text.primary",textStyle:"label/lg",marginRight:"auto",fontWeight:"bold",display:"flex",flexDir:"column"},checkedIcon:{zIndex:"zLayer",w:12,h:10},uncheckedIcon:{zIndex:"zLayer",w:10,h:10,lg:{w:12,h:12}}},variants:{labelPosition:{left:{wrapper:{flexDir:"row"}},right:{wrapper:{flexDir:"row-reverse"}}}},defaultVariants:{labelPosition:"left"}});e.s(["SwitchToggle",0,function(e){let t,o,i,d,m,p,h,f,g,v,y,w,S,b,x,T,k=(0,a.c)(37),{id:C,label:D,onCheckedChange:E,defaultChecked:R,labelPosition:I,children:j}=e;if(k[0]!==j||k[1]!==R||k[2]!==C||k[3]!==D||k[4]!==I||k[5]!==E){let e=u({labelPosition:I});y=e.wrapper,w=(0,r.jsxs)("label",{className:e.label,htmlFor:C,children:[D,j]}),i=s.Switch.Root,h=e.switchRoot,f=C,g=E,v=R,o=s.Switch.Thumb,m=e.switchThumb,p=(0,r.jsx)(l,{className:(0,c.cx)(e.uncheckedIcon,"unchecked")}),t=n.default,d=(0,c.cx)(e.checkedIcon,"checked"),k[0]=j,k[1]=R,k[2]=C,k[3]=D,k[4]=I,k[5]=E,k[6]=t,k[7]=o,k[8]=i,k[9]=d,k[10]=m,k[11]=p,k[12]=h,k[13]=f,k[14]=g,k[15]=v,k[16]=y,k[17]=w}else t=k[6],o=k[7],i=k[8],d=k[9],m=k[10],p=k[11],h=k[12],f=k[13],g=k[14],v=k[15],y=k[16],w=k[17];return k[18]!==t||k[19]!==d?(S=(0,r.jsx)(t,{className:d}),k[18]=t,k[19]=d,k[20]=S):S=k[20],k[21]!==o||k[22]!==S||k[23]!==m||k[24]!==p?(b=(0,r.jsxs)(o,{className:m,children:[p,S]}),k[21]=o,k[22]=S,k[23]=m,k[24]=p,k[25]=b):b=k[25],k[26]!==i||k[27]!==b||k[28]!==h||k[29]!==f||k[30]!==g||k[31]!==v?(x=(0,r.jsx)(i,{className:h,id:f,onCheckedChange:g,defaultChecked:v,children:b}),k[26]=i,k[27]=b,k[28]=h,k[29]=f,k[30]=g,k[31]=v,k[32]=x):x=k[32],k[33]!==x||k[34]!==y||k[35]!==w?(T=(0,r.jsxs)("div",{className:y,children:[w,x]}),k[33]=x,k[34]=y,k[35]=w,k[36]=T):T=k[36],T}],623664)},684496,e=>{"use strict";e.s(["getTimeParts",0,function(e,t,r){let a=new Date(e),s=new Intl.DateTimeFormat(t,{hour:r?"2-digit":"numeric",minute:r?"2-digit":"numeric"}).formatToParts(a),n=s.find(e=>"hour"===e.type)?.value??"",o=s.find(e=>"literal"===e.type)?.value??"";return{hour:n,literal:o,minute:s.find(e=>"minute"===e.type)?.value??"",ampm:s.find(e=>"dayPeriod"===e.type)?.value}}])}]);

//# sourceMappingURL=0q77quo8kruly.js.map