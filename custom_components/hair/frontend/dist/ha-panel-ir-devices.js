function e(e,t,i,s){var r,o=arguments.length,a=o<3?t:null===s?s=Object.getOwnPropertyDescriptor(t,i):s;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)a=Reflect.decorate(e,t,i,s);else for(var n=e.length-1;n>=0;n--)(r=e[n])&&(a=(o<3?r(a):o>3?r(t,i,a):r(t,i))||a);return o>3&&a&&Object.defineProperty(t,i,a),a}"function"==typeof SuppressedError&&SuppressedError;const t=globalThis,i=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,s=Symbol(),r=new WeakMap;let o=class{constructor(e,t,i){if(this._$cssResult$=!0,i!==s)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(i&&void 0===e){const i=void 0!==t&&1===t.length;i&&(e=r.get(t)),void 0===e&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),i&&r.set(t,e))}return e}toString(){return this.cssText}};const a=(e,...t)=>{const i=1===e.length?e[0]:t.reduce((t,i,s)=>t+(e=>{if(!0===e._$cssResult$)return e.cssText;if("number"==typeof e)return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+e[s+1],e[0]);return new o(i,e,s)},n=i?e=>e:e=>e instanceof CSSStyleSheet?(e=>{let t="";for(const i of e.cssRules)t+=i.cssText;return(e=>new o("string"==typeof e?e:e+"",void 0,s))(t)})(e):e,{is:l,defineProperty:d,getOwnPropertyDescriptor:c,getOwnPropertyNames:p,getOwnPropertySymbols:h,getPrototypeOf:g}=Object,m=globalThis,u=m.trustedTypes,_=u?u.emptyScript:"",v=m.reactiveElementPolyfillSupport,b=(e,t)=>e,f={toAttribute(e,t){switch(t){case Boolean:e=e?_:null;break;case Object:case Array:e=null==e?e:JSON.stringify(e)}return e},fromAttribute(e,t){let i=e;switch(t){case Boolean:i=null!==e;break;case Number:i=null===e?null:Number(e);break;case Object:case Array:try{i=JSON.parse(e)}catch(e){i=null}}return i}},y=(e,t)=>!l(e,t),x={attribute:!0,type:String,converter:f,reflect:!1,useDefault:!1,hasChanged:y};Symbol.metadata??=Symbol("metadata"),m.litPropertyMetadata??=new WeakMap;let $=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=x){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const i=Symbol(),s=this.getPropertyDescriptor(e,i,t);void 0!==s&&d(this.prototype,e,s)}}static getPropertyDescriptor(e,t,i){const{get:s,set:r}=c(this.prototype,e)??{get(){return this[t]},set(e){this[t]=e}};return{get:s,set(t){const o=s?.call(this);r?.call(this,t),this.requestUpdate(e,o,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??x}static _$Ei(){if(this.hasOwnProperty(b("elementProperties")))return;const e=g(this);e.finalize(),void 0!==e.l&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(b("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(b("properties"))){const e=this.properties,t=[...p(e),...h(e)];for(const i of t)this.createProperty(i,e[i])}const e=this[Symbol.metadata];if(null!==e){const t=litPropertyMetadata.get(e);if(void 0!==t)for(const[e,i]of t)this.elementProperties.set(e,i)}this._$Eh=new Map;for(const[e,t]of this.elementProperties){const i=this._$Eu(e,t);void 0!==i&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const i=new Set(e.flat(1/0).reverse());for(const e of i)t.unshift(n(e))}else void 0!==e&&t.push(n(e));return t}static _$Eu(e,t){const i=t.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof e?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),void 0!==this.renderRoot&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const i of t.keys())this.hasOwnProperty(i)&&(e.set(i,this[i]),delete this[i]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((e,s)=>{if(i)e.adoptedStyleSheets=s.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(const i of s){const s=document.createElement("style"),r=t.litNonce;void 0!==r&&s.setAttribute("nonce",r),s.textContent=i.cssText,e.appendChild(s)}})(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,i){this._$AK(e,i)}_$ET(e,t){const i=this.constructor.elementProperties.get(e),s=this.constructor._$Eu(e,i);if(void 0!==s&&!0===i.reflect){const r=(void 0!==i.converter?.toAttribute?i.converter:f).toAttribute(t,i.type);this._$Em=e,null==r?this.removeAttribute(s):this.setAttribute(s,r),this._$Em=null}}_$AK(e,t){const i=this.constructor,s=i._$Eh.get(e);if(void 0!==s&&this._$Em!==s){const e=i.getPropertyOptions(s),r="function"==typeof e.converter?{fromAttribute:e.converter}:void 0!==e.converter?.fromAttribute?e.converter:f;this._$Em=s;const o=r.fromAttribute(t,e.type);this[s]=o??this._$Ej?.get(s)??o,this._$Em=null}}requestUpdate(e,t,i,s=!1,r){if(void 0!==e){const o=this.constructor;if(!1===s&&(r=this[e]),i??=o.getPropertyOptions(e),!((i.hasChanged??y)(r,t)||i.useDefault&&i.reflect&&r===this._$Ej?.get(e)&&!this.hasAttribute(o._$Eu(e,i))))return;this.C(e,t,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(e,t,{useDefault:i,reflect:s,wrapped:r},o){i&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,o??t??this[e]),!0!==r||void 0!==o)||(this._$AL.has(e)||(this.hasUpdated||i||(t=void 0),this._$AL.set(e,t)),!0===s&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}const e=this.scheduleUpdate();return null!=e&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[e,t]of this._$Ep)this[e]=t;this._$Ep=void 0}const e=this.constructor.elementProperties;if(e.size>0)for(const[t,i]of e){const{wrapped:e}=i,s=this[t];!0!==e||this._$AL.has(t)||void 0===s||this.C(t,void 0,i,s)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(e=>e.hostUpdate?.()),this.update(t)):this._$EM()}catch(t){throw e=!1,this._$EM(),t}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(e){}firstUpdated(e){}};$.elementStyles=[],$.shadowRootOptions={mode:"open"},$[b("elementProperties")]=new Map,$[b("finalized")]=new Map,v?.({ReactiveElement:$}),(m.reactiveElementVersions??=[]).push("2.1.2");const w=globalThis,k=e=>e,C=w.trustedTypes,S=C?C.createPolicy("lit-html",{createHTML:e=>e}):void 0,D="$lit$",A=`lit$${Math.random().toFixed(9).slice(2)}$`,T="?"+A,E=`<${T}>`,I=document,P=()=>I.createComment(""),R=e=>null===e||"object"!=typeof e&&"function"!=typeof e,M=Array.isArray,H="[ \t\n\f\r]",z=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,N=/-->/g,L=/>/g,V=RegExp(`>|${H}(?:([^\\s"'>=/]+)(${H}*=${H}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),O=/'/g,q=/"/g,U=/^(?:script|style|textarea|title)$/i,F=(e,...t)=>({_$litType$:1,strings:e,values:t}),j=Symbol.for("lit-noChange"),B=Symbol.for("lit-nothing"),X=new WeakMap,Z=I.createTreeWalker(I,129);function W(e,t){if(!M(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==S?S.createHTML(t):t}class Y{constructor({strings:e,_$litType$:t},i){let s;this.parts=[];let r=0,o=0;const a=e.length-1,n=this.parts,[l,d]=((e,t)=>{const i=e.length-1,s=[];let r,o=2===t?"<svg>":3===t?"<math>":"",a=z;for(let t=0;t<i;t++){const i=e[t];let n,l,d=-1,c=0;for(;c<i.length&&(a.lastIndex=c,l=a.exec(i),null!==l);)c=a.lastIndex,a===z?"!--"===l[1]?a=N:void 0!==l[1]?a=L:void 0!==l[2]?(U.test(l[2])&&(r=RegExp("</"+l[2],"g")),a=V):void 0!==l[3]&&(a=V):a===V?">"===l[0]?(a=r??z,d=-1):void 0===l[1]?d=-2:(d=a.lastIndex-l[2].length,n=l[1],a=void 0===l[3]?V:'"'===l[3]?q:O):a===q||a===O?a=V:a===N||a===L?a=z:(a=V,r=void 0);const p=a===V&&e[t+1].startsWith("/>")?" ":"";o+=a===z?i+E:d>=0?(s.push(n),i.slice(0,d)+D+i.slice(d)+A+p):i+A+(-2===d?t:p)}return[W(e,o+(e[i]||"<?>")+(2===t?"</svg>":3===t?"</math>":"")),s]})(e,t);if(this.el=Y.createElement(l,i),Z.currentNode=this.el.content,2===t||3===t){const e=this.el.content.firstChild;e.replaceWith(...e.childNodes)}for(;null!==(s=Z.nextNode())&&n.length<a;){if(1===s.nodeType){if(s.hasAttributes())for(const e of s.getAttributeNames())if(e.endsWith(D)){const t=d[o++],i=s.getAttribute(e).split(A),a=/([.?@])?(.*)/.exec(t);n.push({type:1,index:r,name:a[2],strings:i,ctor:"."===a[1]?ee:"?"===a[1]?te:"@"===a[1]?ie:Q}),s.removeAttribute(e)}else e.startsWith(A)&&(n.push({type:6,index:r}),s.removeAttribute(e));if(U.test(s.tagName)){const e=s.textContent.split(A),t=e.length-1;if(t>0){s.textContent=C?C.emptyScript:"";for(let i=0;i<t;i++)s.append(e[i],P()),Z.nextNode(),n.push({type:2,index:++r});s.append(e[t],P())}}}else if(8===s.nodeType)if(s.data===T)n.push({type:2,index:r});else{let e=-1;for(;-1!==(e=s.data.indexOf(A,e+1));)n.push({type:7,index:r}),e+=A.length-1}r++}}static createElement(e,t){const i=I.createElement("template");return i.innerHTML=e,i}}function G(e,t,i=e,s){if(t===j)return t;let r=void 0!==s?i._$Co?.[s]:i._$Cl;const o=R(t)?void 0:t._$litDirective$;return r?.constructor!==o&&(r?._$AO?.(!1),void 0===o?r=void 0:(r=new o(e),r._$AT(e,i,s)),void 0!==s?(i._$Co??=[])[s]=r:i._$Cl=r),void 0!==r&&(t=G(e,r._$AS(e,t.values),r,s)),t}class K{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:i}=this._$AD,s=(e?.creationScope??I).importNode(t,!0);Z.currentNode=s;let r=Z.nextNode(),o=0,a=0,n=i[0];for(;void 0!==n;){if(o===n.index){let t;2===n.type?t=new J(r,r.nextSibling,this,e):1===n.type?t=new n.ctor(r,n.name,n.strings,this,e):6===n.type&&(t=new se(r,this,e)),this._$AV.push(t),n=i[++a]}o!==n?.index&&(r=Z.nextNode(),o++)}return Z.currentNode=I,s}p(e){let t=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(e,i,t),t+=i.strings.length-2):i._$AI(e[t])),t++}}class J{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,i,s){this.type=2,this._$AH=B,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=i,this.options=s,this._$Cv=s?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return void 0!==t&&11===e?.nodeType&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=G(this,e,t),R(e)?e===B||null==e||""===e?(this._$AH!==B&&this._$AR(),this._$AH=B):e!==this._$AH&&e!==j&&this._(e):void 0!==e._$litType$?this.$(e):void 0!==e.nodeType?this.T(e):(e=>M(e)||"function"==typeof e?.[Symbol.iterator])(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==B&&R(this._$AH)?this._$AA.nextSibling.data=e:this.T(I.createTextNode(e)),this._$AH=e}$(e){const{values:t,_$litType$:i}=e,s="number"==typeof i?this._$AC(e):(void 0===i.el&&(i.el=Y.createElement(W(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===s)this._$AH.p(t);else{const e=new K(s,this),i=e.u(this.options);e.p(t),this.T(i),this._$AH=e}}_$AC(e){let t=X.get(e.strings);return void 0===t&&X.set(e.strings,t=new Y(e)),t}k(e){M(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let i,s=0;for(const r of e)s===t.length?t.push(i=new J(this.O(P()),this.O(P()),this,this.options)):i=t[s],i._$AI(r),s++;s<t.length&&(this._$AR(i&&i._$AB.nextSibling,s),t.length=s)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){const t=k(e).nextSibling;k(e).remove(),e=t}}setConnected(e){void 0===this._$AM&&(this._$Cv=e,this._$AP?.(e))}}class Q{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,i,s,r){this.type=1,this._$AH=B,this._$AN=void 0,this.element=e,this.name=t,this._$AM=s,this.options=r,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=B}_$AI(e,t=this,i,s){const r=this.strings;let o=!1;if(void 0===r)e=G(this,e,t,0),o=!R(e)||e!==this._$AH&&e!==j,o&&(this._$AH=e);else{const s=e;let a,n;for(e=r[0],a=0;a<r.length-1;a++)n=G(this,s[i+a],t,a),n===j&&(n=this._$AH[a]),o||=!R(n)||n!==this._$AH[a],n===B?e=B:e!==B&&(e+=(n??"")+r[a+1]),this._$AH[a]=n}o&&!s&&this.j(e)}j(e){e===B?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class ee extends Q{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===B?void 0:e}}class te extends Q{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==B)}}class ie extends Q{constructor(e,t,i,s,r){super(e,t,i,s,r),this.type=5}_$AI(e,t=this){if((e=G(this,e,t,0)??B)===j)return;const i=this._$AH,s=e===B&&i!==B||e.capture!==i.capture||e.once!==i.once||e.passive!==i.passive,r=e!==B&&(i===B||s);s&&this.element.removeEventListener(this.name,this,i),r&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}}class se{constructor(e,t,i){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(e){G(this,e)}}const re={I:J},oe=w.litHtmlPolyfillSupport;oe?.(Y,J),(w.litHtmlVersions??=[]).push("3.3.3");const ae=globalThis;let ne=class extends ${constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=((e,t,i)=>{const s=i?.renderBefore??t;let r=s._$litPart$;if(void 0===r){const e=i?.renderBefore??null;s._$litPart$=r=new J(t.insertBefore(P(),e),e,void 0,i??{})}return r._$AI(e),r})(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return j}};ne._$litElement$=!0,ne.finalized=!0,ae.litElementHydrateSupport?.({LitElement:ne});const le=ae.litElementPolyfillSupport;le?.({LitElement:ne}),(ae.litElementVersions??=[]).push("4.2.2");const de={attribute:!0,type:String,converter:f,reflect:!1,hasChanged:y},ce=(e=de,t,i)=>{const{kind:s,metadata:r}=i;let o=globalThis.litPropertyMetadata.get(r);if(void 0===o&&globalThis.litPropertyMetadata.set(r,o=new Map),"setter"===s&&((e=Object.create(e)).wrapped=!0),o.set(i.name,e),"accessor"===s){const{name:s}=i;return{set(i){const r=t.get.call(this);t.set.call(this,i),this.requestUpdate(s,r,e,!0,i)},init(t){return void 0!==t&&this.C(s,void 0,e,t),t}}}if("setter"===s){const{name:s}=i;return function(i){const r=this[s];t.call(this,i),this.requestUpdate(s,r,e,!0,i)}}throw Error("Unsupported decorator location: "+s)};function pe(e){return(t,i)=>"object"==typeof i?ce(e,t,i):((e,t,i)=>{const s=t.hasOwnProperty(i);return t.constructor.createProperty(i,e),s?Object.getOwnPropertyDescriptor(t,i):void 0})(e,t,i)}function he(e){return pe({...e,state:!0,attribute:!1})}const ge=e=>e,me=e=>customElements.get(e)?ge:(e=>(t,i)=>{void 0!==i?i.addInitializer(()=>{customElements.define(e,t)}):customElements.define(e,t)})(e);class ue{constructor(e){this.hass=e}listDevices(){return this.hass.connection.sendMessagePromise({type:"hair/devices"})}getDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/device",device_id:e})}createDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/device/create",...e})}updateDevice(e,t){return this.hass.connection.sendMessagePromise({type:"hair/device/update",device_id:e,...t})}deleteDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/device/delete",device_id:e})}duplicateDevice(e,t){return this.hass.connection.sendMessagePromise({type:"hair/device/duplicate",device_id:e,new_name:t})}deleteCommand(e,t){return this.hass.connection.sendMessagePromise({type:"hair/command/delete",device_id:e,command_id:t})}setCommandTxForceRaw(e,t,i){return this.hass.connection.sendMessagePromise({type:"hair/command/set-tx-force-raw",device_id:e,command_id:t,tx_force_raw:i})}reorderCommands(e,t){return this.hass.connection.sendMessagePromise({type:"hair/device/reorder-commands",device_id:e,command_ids:t})}reorderDevices(e){return this.hass.connection.sendMessagePromise({type:"hair/devices/reorder",device_ids:e})}sendCommand(e,t){return this.hass.connection.sendMessagePromise({type:"hair/command/send",device_id:e,command_id:t})}listTemplates(e){return this.hass.connection.sendMessagePromise({type:"hair/templates",device_type:e})}listCaptureProviders(){return this.hass.connection.sendMessagePromise({type:"hair/capture/providers"})}listReceivers(){return this.hass.connection.sendMessagePromise({type:"hair/receivers"})}getSnifferStatus(){return this.hass.connection.sendMessagePromise({type:"hair/sniffer/status"})}getCodeBrands(){return this.hass.connection.sendMessagePromise({type:"hair/codes/brands"})}importCodeRemote(e,t){const i={type:"hair/codes/import-remote",codebook_id:e};return t&&(i.name=t),this.hass.connection.sendMessagePromise(i)}async startCapture(e,t,i){let s=null;const r=await this.hass.connection.subscribeMessage(e=>{e.type?.startsWith("capture_")?i(e):e.session_id&&(s=e)},{type:"hair/capture/start",device_id:e,timeout:t});if(await Promise.resolve(),null===s)throw new Error("Capture session did not start");return{session:s,unsubscribe:r}}cancelCapture(e){return this.hass.connection.sendMessagePromise({type:"hair/capture/cancel",session_id:e})}saveCapturedCommand(e){return this.hass.connection.sendMessagePromise({type:"hair/capture/save",...e})}getActionOptions(e){return this.hass.connection.sendMessagePromise({type:"hair/device/action-options",device_type:e})}updateMapping(e,t,i){return this.hass.connection.sendMessagePromise({type:"hair/device/update-mapping",device_id:e,command_name:t,action_key:i})}getUnknownDevices(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/devices",...e})}getUnknownDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/device",device_id:e})}dismissUnknown(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/dismiss",device_id:e})}undismissUnknown(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/undismiss",device_id:e})}assignSignal(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/assign",...e})}assignToNewDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/assign-new-device",...e})}deleteSignal(e,t){return this.hass.connection.sendMessagePromise({type:"hair/unknown/signal/delete",device_id:e,signal_id:t})}testSignal(e,t){const i={type:"hair/unknown/test",signal_id:e};return t&&(i.emitter_entity_id=t),this.hass.connection.sendMessagePromise(i)}renameUnknown(e,t){return this.hass.connection.sendMessagePromise({type:"hair/unknown/rename",device_id:e,label:t})}clearUnknowns(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/clear",...e?{source:e}:{}})}setSignalAlias(e,t,i){return this.hass.connection.sendMessagePromise({type:"hair/unknown/signal/set-alias",device_id:e,signal_id:t,alias:i})}reorderUnknownDevices(e,t){return this.hass.connection.sendMessagePromise({type:"hair/unknown/reorder",source:e,device_ids:t})}reorderUnknownSignals(e,t){return this.hass.connection.sendMessagePromise({type:"hair/unknown/signal/reorder",device_id:e,signal_ids:t})}createRemote(e){return this.hass.connection.sendMessagePromise({type:"hair/clip/create-remote",name:e})}createSignal(e){return this.hass.connection.sendMessagePromise({type:"hair/clip/create-signal",...e})}editSignalPronto(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/signal/edit-pronto",...e})}validatePronto(e){return this.hass.connection.sendMessagePromise({type:"hair/clip/validate-pronto",pronto:e})}snapPreview(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/signal/snap-preview",...e})}updateCommand(e){return this.hass.connection.sendMessagePromise({type:"hair/command/update",...e})}deleteRemote(e){return this.hass.connection.sendMessagePromise({type:"hair/clip/delete-remote",device_id:e})}listPluckVendors(){return this.hass.connection.sendMessagePromise({type:"hair/pluck/list-vendors"})}runPluck(e){return this.hass.connection.sendMessagePromise({type:"hair/pluck/run",...e})}createPluckedBlaster(e){return this.hass.connection.sendMessagePromise({type:"hair/pluck/create-blaster",...e})}createPluckedSignal(e){return this.hass.connection.sendMessagePromise({type:"hair/pluck/create-signal",...e})}deletePluckedBlaster(e){return this.hass.connection.sendMessagePromise({type:"hair/pluck/delete-blaster",device_id:e})}async subscribeUnknownSignals(e){return this.hass.connection.subscribeEvents(t=>e(t.data),"hair_signal_detected")}async subscribeSignalRemoved(e){return this.hass.connection.subscribeEvents(t=>e(t.data),"hair_signal_removed")}async subscribeSignalUpdated(e){return this.hass.connection.subscribeEvents(t=>e(t.data),"hair_signal_updated")}async subscribeDismissActivity(e){return this.hass.connection.subscribeEvents(t=>e(t.data),"hair_dismiss_activity")}listTriggers(){return this.hass.connection.sendMessagePromise({type:"hair/triggers"})}createTrigger(e){return this.hass.connection.sendMessagePromise({type:"hair/trigger/create",...e})}updateTrigger(e,t){return this.hass.connection.sendMessagePromise({type:"hair/trigger/update",trigger_id:e,...t})}deleteTrigger(e){return this.hass.connection.sendMessagePromise({type:"hair/trigger/delete",trigger_id:e})}async subscribeTriggerFired(e){return this.hass.connection.subscribeMessage(e,{type:"hair/trigger/subscribe"})}}var _e={"_meta.review":"source","panel.loading":"Loading…","panel.load_failed":"Failed to load devices: {message}","panel.open_menu":"Open menu","panel.tab.devices":"Devices","panel.tagline.devices":"Manage your IR devices and the hardware that drives them.","panel.tagline.sniffer":"Capture IR codes live from the air.","panel.tagline.clips":"Build remotes by pasting known IR codes.","panel.tagline.plucker":"Pluck IR codes from existing blasters.","panel.tagline.mirror":"See your live Home Assistant infrared transmissions.","common.confirm":"Confirm","common.cancel":"Cancel","common.are_you_sure":"Are you sure?","common.remove":"Remove","alias.placeholder":"Alias for this signal","alias.clear":"Clear alias","alias.edit":"Click to edit alias","alias.name":"Click to name this signal","picker.emitters_label":"IR emitters","picker.add_emitter":"+ Add emitter...","picker.no_emitters":"No IR emitters found.","picker.all_emitters_selected":"All emitters selected.","picker.receivers_label":"Via receiver(s):","picker.add_receiver":"+ Add receiver...","picker.no_receivers":"No IR receivers found.","picker.all_receivers_selected":"All receivers selected.","device_type.media_player":"Media Player","device_type.ac":"Air Conditioner","device_type.fan":"Fan","device_type.light":"Light","device_type.switch":"Switch","device_type.screen":"Screen / Shade","device_type.other":"Other","common.name":"Name","common.device_type":"Device type","common.name_required":"Name is required.","common.creating":"Creating...","common.device_name_placeholder":"e.g. Living Room TV","promote.heading":"Promote to Device","promote.device_name":"Device name","promote.device_name_required":"Device name is required.","promote.emitter_required":"Select at least one IR emitter.","promote.create_device":"Create Device","adddev.heading":"Add Device","adddev.emitter_required":"Pick at least one IR emitter.","adddev.create":"Create","dup.heading":"Duplicate device","dup.hint_duplicating":"Duplicating {name}.","dup.hint_body":"The new device gets a copy of every command, action mapping, and emitter assignment. You can change anything afterward.","dup.duplicating":"Duplicating...","dup.duplicate":"Duplicate","promote.description":"Create a new HAIR device. You can then assign captured signals to it as commands.","capture.listening":"Listening for IR signal…","capture.instruction":'Point your remote at the IR receiver and press the "{name}" button.',"capture.remaining":"{seconds}s remaining","capture.captured":"Signal Captured!","capture.protocol":"Protocol: {protocol}","capture.protocol_raw":"Raw","capture.verify":"Did it work? Press Test to verify.","capture.test":"▶ Test","capture.recapture":"↻ Re-capture","capture.save_next":"Save & Learn Next ▶▶","capture.no_signal":"⚠ No signal detected","capture.tip_point":"Point the remote directly at the IR receiver","capture.tip_closer":"Move closer (within 3 feet / 1 meter)","capture.tip_hold":"Press and hold the button briefly","capture.try_again":"↻ Try Again","capture.duplicate":"⚠ Duplicate Signal Detected","capture.duplicate_instruction":'This matches your "{name}" command. Some remotes use the same signal for multiple buttons.',"capture.recapture_different":"Re-capture Different","capture.save_anyway":"Save Anyway","capture.error":"⚠ Capture Error","capture.learning":'Learning: "{name}"',"test_emitter.heading":"Send from","test_emitter.sending":"Sending...","test_emitter.send":"Send","createremote.heading":"Create Remote","createremote.type":"Type","createremote.blank":"Blank remote","createremote.from_library":"From code library","createremote.model":"Model","createremote.select_model":"Select a model","popover.assigned_to":"Assigned to","popover.new_assignment":"+ new assignment","popover.open_in_devices":"Open {name} in Devices","popover.triggers":"Triggers","popover.new_trigger":"+ new trigger","popover.any_receiver":"Any receiver","popover.n_more":"{name} + {count} more","cmdrow.rename":"Click to rename","cmdrow.tx_raw_on":"Replaying the captured Pronto. Click to transmit clean decoded packet timings instead.","cmdrow.tx_raw_off":"Transmitting clean decoded packet timings. Click to replay the captured Pronto instead.","cmdrow.sends_times":"Sends this command {count} times","cmdrow.dittos":"Appends {count} NEC dittos","cmdrow.raw_timings":"RAW: {count} timings","cmdrow.not_learned":"Not yet learned","cmdrow.edit_code":"View or edit code","cmdrow.map_action":"Assign action mapping","cmdrow.actions":"ACTIONS","cmdrow.test":"Test","cmdrow.trigger":"Trigger","cmdrow.edit_trigger":"Edit trigger","cmdrow.create_trigger":"Create trigger","cmdrow.delete":"Delete","cmdrow.learn":"Learn","trigger.alias_tag":"alias","trigger.event":"Trigger Event","trigger.edit_heading":"Edit Trigger","trigger.create_heading":"Create Trigger","trigger.mirror_hint":"Fires when this signal arrives from outside Home Assistant (a physical remote or another app), never on the house's own sends.","trigger.name_label":"Trigger Name","trigger.name_placeholder":"e.g. TV Power","trigger.min_hits":"Min Hits","trigger.min_hits_hint":"Number of presses within 5s to fire","trigger.scope_hint":"Fires once per press, regardless of how many scoped receivers observe the signal.","trigger.save_failed":"Save failed","common.saving":"Saving...","common.update":"Update","common.create":"Create","common.delete":"Delete","assign.heading":"Assign Signal","assign.hits":"{count} hits","assign.mode_existing":"Existing Device","assign.mode_new":"New Device","assign.send_times":"Send times","assign.send_times_hint":"Transmit this command this many times per press, for devices that need a repeat. Default 1.","assign.ditto_count":"Ditto count","assign.ditto_title":"Append repeat frames after the main frame; some strict receivers need at least one to register the command.","assign.ditto_hint":"Append repeat frames after the main frame; some strict receivers require at least one to register the command.","assign.assigning":"Assigning...","assign.create_assign":"Create & Assign","assign.assign":"Assign","assign.target_device":"Target device","assign.no_devices":'No devices yet. Switch to "New Device" to create one.',"assign.select_device":"Select device...","assign.command_name":"Command name","assign.command_placeholder":"Enter command name","assign.select_command":"Select command...","assign.custom":"Custom...","assign.command_required":"Command name is required.","assign.target_required":"Select a target device.","assign.failed_duplicate":"Assignment failed. The signal may have a duplicate code on the target device.","pluckdlg.blaster_required":"Pick a blaster to pluck from.","pluckdlg.appliance_required":"Appliance is required.","pluckdlg.add_heading":"Add Blaster","pluckdlg.loading_blasters":"Loading blasters...","pluckdlg.pluck_from":"Pluck from","pluckdlg.select_blaster":"Select a blaster","pluckdlg.appliance":"Appliance","pluckdlg.appliance_placeholder":"e.g. candles","pluckdlg.name_placeholder":"e.g. Living Room candles","pluckdlg.signal_heading":"Pluck Signal","pluckdlg.pluck_failed":"Pluck failed.","pluckdlg.no_response":"No response from blaster. Try again.","pluckdlg.recognized_as":"Recognized as {protocol}","pluckdlg.valid_pronto":"Valid Pronto code","pluckdlg.command_help":"The name you gave this code when you learned it in the vendor app.","pluckdlg.command_placeholder":"e.g. pwr_on","pluckdlg.plucking":"Plucking...","pluckdlg.pluck":"Pluck","pluckdlg.captured":"Captured","pluckdlg.remove_capture":"Remove this capture","pluckdlg.alias":"Alias","pluckdlg.no_blasters":"No compatible blasters found. Install a supported IR integration (such as Tuya Local) and learn a code first.","editor.ditto_disabled_cmd":"Ditto count applies when the command transmits as NEC. Toggle the pill to NEC to enable.","editor.ditto_disabled":"Ditto count applies to decoded signals (NEC today). Raw Pronto codes transmit as captured.","editor.copied":"Copied","editor.press_copy":"Press Cmd/Ctrl+C","editor.valid":"Valid Pronto code","editor.not_valid":"Not valid yet","editor.burst_pair.one":"{count} burst pair","editor.burst_pair.other":"{count} burst pairs","editor.recognized_as":"Recognized as {protocol}","editor.snap_notice":"Carrier is {khz} kHz, off the IR standards. Some receivers reject it.","editor.snapping":"Snapping...","editor.snap_to":"Snap to {khz} kHz","editor.edit_command":"Edit command","editor.edit_signal":"Edit signal","editor.create_signal":"Create signal","common.save":"Save","editor.trigger_note_cmd":"This command has a trigger that will automatically re-point.","editor.trigger_note_sig":"This signal has a trigger that will automatically re-point.","editor.alias_label":"Alias","editor.alias_optional":"Alias (optional)","editor.pronto_code":"Pronto code","editor.select_all":"Select all (then Cmd/Ctrl+C)","editor.alias_placeholder":"e.g. Power","editor.send_times_title":"Transmit the whole command this many times as independent presses, for devices that need a repeat to register.","editor.ditto_title":"Append repeat frames after the main frame. Some strict receivers, notably commercial audio gear, need at least one to register the command.","editor.observed.one":"Observed at capture: {count} ditto","editor.observed.other":"Observed at capture: {count} dittos","rel.just_now":"just now","mirror.via":"via {name}","mirror.via_n":"via {count} emitters","mirror.not_heard":"not heard","mirror.heard_in":"last heard in {areas}","mirror.heard_by":"last heard by {names}","mirror.chip_automation":"Automation Send","mirror.chip_integration":"Integration Send","mirror.chip_test":"Manual Test Send","mirror.chip_device":"HAIR Device","mirror.chip_send":"Send","mirror.unknown_title":"Unknown IR signal sent","mirror.unknown_hint":"{name} fired, but nothing was close enough to hear what it said. Place a receiver in earshot to catch the next send.","mirror.the_blaster":"The blaster","mirror.sent":"Sent!","mirror.sent_all_n":"Sent! ({sent}/{total})","mirror.sent_partial":"Sent ({sent}/{total})","mirror.failed":"Failed","mirror.error":"Error","mirror.sending":"Sending...","mirror.test":"Test","mirror.stat_sends":"SENDS","mirror.stat_not_heard":"NOT HEARD","mirror.stat_emitters":"EMITTERS","mirror.stat_signals":"SIGNALS","mirror.last_send_ago":"last send {rel} ago","mirror.last_send_just":"last send just now","mirror.no_receivers":"no receivers","mirror.filter_all":"All ({count})","mirror.filter_not_heard":"Not heard ({count})","mirror.search":"Search sends...","mirror.no_match":"No sends match.","mirror.signals.one":"{count} signal","mirror.signals.other":"{count} signals","mirror.sends_times":"Sends this signal {count} times","mirror.assign_disabled":"Identity unknown -- nothing was heard back to assign","mirror.assigned_one":"Assigned to {device} / {command}","mirror.assigned_n":"Assigned to {count} commands:","mirror.assign_title":"Assign this signal to a HAIR device","mirror.test_title":"Send this signal through an emitter to test it","mirror.test_disabled":"Identity unknown -- nothing to send","mirror.trigger_disabled":"Identity unknown -- nothing to bind","mirror.trigger_edit":"Edit trigger(s) for this signal","mirror.trigger_create":"Fires when this signal arrives from outside Home Assistant","mirror.delete_title":"Clear this entry (it returns on the next send)","mirror.empty_title":"Nothing sent yet","mirror.empty_sub":"Commands sent by HAIR devices, automations, or any integration on the infrared platform will appear here, with where they went and who heard them.","mirror.del_trigger_title":"Delete Trigger","mirror.del_trigger_msg":"Remove this trigger permanently? Automations using it will stop firing.","mirror.clear_title":"Clear Mirror Entry","mirror.clear_msg":"Remove this entry from the Mirror? It will come back the next time this signal is sent.","common.delete_failed":"Delete failed: {message}","device_type.other_card":"IR Device","devlist.loading":"Loading IR devices...","devlist.empty_title":"No IR devices yet","devlist.empty_sub":"Add your first device to get started.","devlist.add_device_plus":"+ Add Device","devlist.title":"HAIR Devices","devlist.add_device":"Add Device","devlist.cmd_badge":"CMD: {count}","devlist.tx_badge":"TX: {count}","devlist.no_tx":"No TX","devlist.rx_native_title":"Receives via HA's native infrared platform","devlist.rx_bridge_active":"Legacy bridge still active. Native receiver supersedes it -- you can remove the on_pronto: block from your ESPHome config.","devlist.rx_bridge_title":"Receives via legacy ESPHome event-bus bridge","devlist.rx_upgrade_title":"Upgrade to HA 2026.6+ for native receiver support","devlist.tx_native_title":"Sends via HA's native infrared platform","devlist.blasters":"Blasters (Pluckable)","devlist.emitters":"Emitters","devlist.receivers":"Receivers","devlist.proxies":"Proxies","devlist.hits_badge":"{count}x hits","devlist.on":"ON","devlist.off":"OFF","devlist.delete_trigger":"Delete trigger","devlist.delete_device":"Delete device","devlist.open_plucker_title":"Open in the Plucker","devlist.open_plucker":"Open in Plucker","devlist.del_trigger_msg":'Remove "{name}"? The associated HA event entity will also be removed.',"devlist.del_device_title":"Delete Device","devlist.del_device_msg":'Remove "{name}"? Commands, action mappings, and emitter assignments will be deleted. Triggers are unaffected.',"common.close":"Close","devdetail.name_updated":"Name updated","devdetail.type_updated":"Device type updated","devdetail.emitters_updated":"Emitters updated","devdetail.update_failed":"Update failed: {message}","devdetail.reorder_failed":"Reorder failed: {message}","devdetail.mapped_to":"Mapped to {action}","devdetail.mapping_cleared":"Mapping cleared","devdetail.mapping_failed":"Mapping failed: {message}","devdetail.sent_cmd":'Sent "{name}"',"devdetail.send_failed":"Send failed: {message}","devdetail.cmd_updated":"Command updated","devdetail.cmd_updated_repointed":"Command updated. Re-pointed trigger {names}.","devdetail.rename_failed":"Rename failed: {message}","devdetail.removed":'Removed "{name}"',"devdetail.saved":'Saved "{name}"',"devdetail.type":"Type","devdetail.commands":"Commands ({count})","devdetail.no_commands":"No commands yet. Add one below.","devdetail.drag":"Drag to reorder","devdetail.map_action":"Map action","devdetail.none_clear":"None (clear)","devdetail.sniff_title":"Capture a new signal in the Sniffer","devdetail.sniffed":"+ Sniffed Signal","devdetail.clip_title":"Paste a new signal in Clips","devdetail.clipped":"+ Clipped Signal","devdetail.mirror_title":"Overhear a send in the Mirror","devdetail.mirrored":"+ Mirrored Signal","devdetail.del_device_title":"Delete {name}?","devdetail.del_device_msg":"This removes all captured commands and the auto-created entity. The action cannot be undone.","devdetail.del_cmd_title":"Delete command?","devdetail.del_cmd_msg":'Remove "{name}"? This cannot be undone.',"devdetail.del_trigger_msg":"Remove this trigger? The associated HA event entity will also be removed.","rel.min_ago":"{count} min ago","rel.h_ago":"{count}h ago","rel.d_ago":"{count}d ago","sniffer.title":"HAIR Sniffer","sniffer.remotes.one":"{count} remote","sniffer.remotes.other":"{count} remotes","sniffer.scanning":"Scanning for signals...","sniffer.empty_title":"No unknown signals detected","sniffer.empty_body":"When unrecognized IR signals are received by your ESPHome devices, they will appear here automatically.","sniffer.empty_hint":"Try pressing a button on a remote that hasn't been configured yet.","sniffer.norx_title":"No IR receiver is set up","sniffer.norx_body":"HAIR has no way to receive IR signals yet, so the Sniffer cannot capture anything.","sniffer.norx_hint":"Set up an ESPHome receiver with the infrared platform, or check Settings, then Devices and Services, to confirm your IR device is adopted.","sniffer.show_dismissed_title":"Restore previously hidden remotes","sniffer.show_dismissed":"Show Dismissed","sniffer.hide_dismissed":"Hide Dismissed","sniffer.clear_all_title":"Wipe the entire unknown catalog AND the dismiss list. Use Show Dismissed before Clear All if you want to retain individual dismissed entries.","sniffer.clear_all":"Clear All","sniffer.del_signal_title":"Delete Signal","sniffer.del_signal_msg":"Remove this signal permanently? This cannot be undone.","sniffer.clear_all_confirm_title":"Clear All Signals","sniffer.clear_all_confirm_msg":"Remove all unknown signals and devices? This cannot be undone.","sniffer.hair_device":"HAIR Device","sniffer.promote":"Promote","sniffer.dismissed":"dismissed","sniffer.restore":"Restore","sniffer.dismiss":"Dismiss","sniffer.addr":"addr: {address}","sniffer.signals_head":"Signals ({count})","sniffer.first_seen":"First seen: {time}","sniffer.restore_first":"Restore this remote first","sniffer.trigger_create":"Create an HA event entity that fires on this signal","common.raw":"RAW","sniffer.hit_word.one":"hit","sniffer.hit_word.other":"hits","sniffer.signal_word.one":"signal","sniffer.signal_word.other":"signals","common.loading_plain":"Loading...","clips.title":"HAIR Clipper","clips.add_remote":"+ Add Remote","clips.empty_title":"No virtual remotes yet","clips.empty_body":"Clipper lets you build remotes by pasting Pronto codes. Create a remote, then add a signal for each button.","clips.empty_hint":'Click "+ Add Remote" above to start a clipped remote.',"clips.clear_all_title":"Delete all clipped remotes and their signals. Sniffed signals are untouched.","clips.remote_fallback":"Remote","clips.add_signal_title":"Add a signal to this remote","clips.add_signal":"+ Add Signal","clips.no_signals":'No signals yet. Click "+ Add Signal" to paste a Pronto code.',"clips.delete_remote_title":"Delete this remote and all its signals","clips.delete_remote":"Delete remote","clips.test_title":"Send this signal through an emitter","clips.clear_all_confirm_title":"Clear All Clips","clips.clear_all_confirm_msg":"Remove all clipped remotes and their signals? This cannot be undone. Sniffed signals are not affected.","clips.del_remote_confirm_title":"Delete Remote","clips.del_remote_msg_n.one":'Remove "{name}" and its {count} signal? This cannot be undone.',"clips.del_remote_msg_n.other":'Remove "{name}" and its {count} signals? This cannot be undone.',"clips.del_remote_msg":'Remove "{name}"? This cannot be undone.',"pluck.vendor_unavailable":"This blaster's integration is not available right now. Make sure the vendor integration is loaded.","pluck.title":"HAIR Plucker","pluck.add_blaster":"+ Add Blaster","pluck.empty_title":"No plucked blasters yet","pluck.empty_body":"The Plucker imports IR codes from your existing blasters so you can use them in HAIR without re-learning each one.","pluck.empty_hint":'Click "+ Add Blaster" above to mirror a blaster.',"pluck.clear_all_title":"Delete all plucked blasters and their signals. Sniffed and clipped signals are untouched.","pluck.blaster_fallback":"Blaster","pluck.promote_title":"Create a HAIR device from this blaster","pluck.pluck_signal_title":"Pluck a code off this blaster","pluck.pluck_signal":"+ Pluck Signal","pluck.no_signals":'No signals yet. Click "+ Pluck Signal" to pull a code off this blaster.',"pluck.delete_blaster_title":"Delete this blaster and all its signals","pluck.delete_blaster":"Delete blaster","pluck.clear_all_confirm_title":"Clear All Plucked","pluck.clear_all_confirm_msg":"Remove all plucked blasters and their signals? This cannot be undone. Sniffed and clipped signals are not affected.","pluck.del_blaster_confirm_title":"Delete Blaster","devdetail.custom_action":"Custom...","devdetail.custom_action_placeholder":"e.g. temp_30","devdetail.set":"Set","vocab.back_return":"Back/Return","vocab.brightness_down":"Brightness Down","vocab.brightness_up":"Brightness Up","vocab.channel_down":"Channel Down","vocab.channel_up":"Channel Up","vocab.close":"Close","vocab.color_temp_cooler":"Color Temp Cooler","vocab.color_temp_warmer":"Color Temp Warmer","vocab.down":"Down","vocab.fan_auto":"Fan: Auto","vocab.fan_high":"Fan: High","vocab.fan_low":"Fan: Low","vocab.fan_medium":"Fan: Medium","vocab.fast_forward":"Fast Forward","vocab.guide":"Guide","vocab.left":"Left","vocab.menu":"Menu","vocab.mode_auto":"Mode: Auto","vocab.mode_cool":"Mode: Cool","vocab.mode_dry":"Mode: Dry","vocab.mode_fan":"Mode: Fan","vocab.mode_heat":"Mode: Heat","vocab.mute":"Mute","vocab.off":"Off","vocab.on":"On","vocab.open":"Open","vocab.oscillate":"Oscillate","vocab.pause":"Pause","vocab.play":"Play","vocab.power":"Power","vocab.power_off":"Power Off","vocab.power_on":"Power On","vocab.power_toggle":"Power Toggle","vocab.rewind":"Rewind","vocab.right":"Right","vocab.select_ok":"Select/OK","vocab.source_input":"Source/Input","vocab.speed_down":"Speed Down","vocab.speed_up":"Speed Up","vocab.stop":"Stop","vocab.swing_toggle":"Swing Toggle","vocab.timer":"Timer","vocab.up":"Up","vocab.volume_down":"Volume Down","vocab.volume_up":"Volume Up"};const ve={en:_e,fr:{"_meta.review":"AI draft (2026-07-19), not yet reviewed by a native speaker -- help wanted, see CONTRIBUTING 'Adding a language'","panel.loading":"Chargement…","panel.load_failed":"Échec du chargement des appareils : {message}","panel.open_menu":"Ouvrir le menu","panel.tab.devices":"Appareils","panel.tagline.devices":"Gérez vos appareils IR et le matériel qui les pilote.","panel.tagline.sniffer":"Capturez des codes IR en direct dans l'air.","panel.tagline.clips":"Créez des télécommandes en collant des codes IR connus.","panel.tagline.plucker":"Cueillez des codes IR depuis vos blasters existants.","panel.tagline.mirror":"Visualisez en direct les transmissions infrarouges de Home Assistant.","common.confirm":"Confirmer","common.cancel":"Annuler","common.are_you_sure":"Êtes-vous sûr ?","common.remove":"Retirer","alias.placeholder":"Alias pour ce signal","alias.clear":"Effacer l'alias","alias.edit":"Cliquez pour modifier l'alias","alias.name":"Cliquez pour nommer ce signal","picker.emitters_label":"Émetteurs IR","picker.add_emitter":"+ Ajouter un émetteur...","picker.no_emitters":"Aucun émetteur IR trouvé.","picker.all_emitters_selected":"Tous les émetteurs sont sélectionnés.","picker.receivers_label":"Via récepteur(s) :","picker.add_receiver":"+ Ajouter un récepteur...","picker.no_receivers":"Aucun récepteur IR trouvé.","picker.all_receivers_selected":"Tous les récepteurs sont sélectionnés.","device_type.media_player":"Lecteur multimédia","device_type.ac":"Climatiseur","device_type.fan":"Ventilateur","device_type.light":"Lumière","device_type.switch":"Interrupteur","device_type.screen":"Écran / Store","device_type.other":"Autre","common.name":"Nom","common.device_type":"Type d'appareil","common.name_required":"Le nom est requis.","common.creating":"Création...","common.device_name_placeholder":"ex. TV du salon","promote.heading":"Promouvoir en appareil","promote.device_name":"Nom de l'appareil","promote.device_name_required":"Le nom de l'appareil est requis.","promote.emitter_required":"Sélectionnez au moins un émetteur IR.","promote.create_device":"Créer l'appareil","adddev.heading":"Ajouter un appareil","adddev.emitter_required":"Choisissez au moins un émetteur IR.","adddev.create":"Créer","dup.heading":"Dupliquer l'appareil","dup.hint_duplicating":"Duplication de {name}.","dup.hint_body":"Le nouvel appareil reçoit une copie de chaque commande, mappage d'action et assignation d'émetteur. Vous pourrez tout modifier ensuite.","dup.duplicating":"Duplication...","dup.duplicate":"Dupliquer","promote.description":"Créez un nouvel appareil HAIR. Vous pourrez ensuite lui assigner des signaux capturés comme commandes.","capture.listening":"En écoute d'un signal IR…","capture.instruction":'Pointez votre télécommande vers le récepteur IR et appuyez sur le bouton "{name}".',"capture.remaining":"{seconds}s restantes","capture.captured":"Signal capturé !","capture.protocol":"Protocole : {protocol}","capture.protocol_raw":"Brut","capture.verify":"Ça a fonctionné ? Appuyez sur Test pour vérifier.","capture.test":"▶ Test","capture.recapture":"↻ Recapturer","capture.save_next":"Enregistrer et apprendre le suivant ▶▶","capture.no_signal":"⚠ Aucun signal détecté","capture.tip_point":"Pointez la télécommande directement vers le récepteur IR","capture.tip_closer":"Rapprochez-vous (à moins de 1 mètre)","capture.tip_hold":"Appuyez brièvement sur le bouton en le maintenant","capture.try_again":"↻ Réessayer","capture.duplicate":"⚠ Signal en double détecté","capture.duplicate_instruction":'Ce signal correspond à votre commande "{name}". Certaines télécommandes utilisent le même signal pour plusieurs boutons.',"capture.recapture_different":"Recapturer un autre","capture.save_anyway":"Enregistrer quand même","capture.error":"⚠ Erreur de capture","capture.learning":'Apprentissage : "{name}"',"test_emitter.heading":"Envoyer depuis","test_emitter.sending":"Envoi...","test_emitter.send":"Envoyer","createremote.heading":"Créer une télécommande","createremote.type":"Type","createremote.blank":"Télécommande vierge","createremote.from_library":"Depuis la bibliothèque de codes","createremote.model":"Modèle","createremote.select_model":"Sélectionnez un modèle","popover.assigned_to":"Assigné à","popover.new_assignment":"+ nouvelle assignation","popover.open_in_devices":"Ouvrir {name} dans Appareils","popover.triggers":"Déclencheurs","popover.new_trigger":"+ nouveau déclencheur","popover.any_receiver":"N'importe quel récepteur","popover.n_more":"{name} + {count} autres","cmdrow.rename":"Cliquez pour renommer","cmdrow.tx_raw_on":"Rejoue le Pronto capturé. Cliquez pour transmettre à la place les timings de paquet décodés propres.","cmdrow.tx_raw_off":"Transmet les timings de paquet décodés propres. Cliquez pour rejouer à la place le Pronto capturé.","cmdrow.sends_times":"Envoie cette commande {count} fois","cmdrow.dittos":"Ajoute {count} dittos NEC","cmdrow.raw_timings":"BRUT : {count} timings","cmdrow.not_learned":"Pas encore appris","cmdrow.edit_code":"Voir ou modifier le code","cmdrow.map_action":"Assigner un mappage d'action","cmdrow.actions":"ACTIONS","cmdrow.test":"Test","cmdrow.trigger":"Déclencheur","cmdrow.edit_trigger":"Modifier le déclencheur","cmdrow.create_trigger":"Créer un déclencheur","cmdrow.delete":"Supprimer","cmdrow.learn":"Apprendre","trigger.alias_tag":"alias","trigger.event":"Événement déclencheur","trigger.edit_heading":"Modifier le déclencheur","trigger.create_heading":"Créer un déclencheur","trigger.mirror_hint":"Se déclenche quand ce signal arrive de l'extérieur de Home Assistant (une télécommande physique ou une autre application), jamais sur les envois de la maison elle-même.","trigger.name_label":"Nom du déclencheur","trigger.name_placeholder":"ex. Alimentation TV","trigger.min_hits":"Appuis min","trigger.min_hits_hint":"Nombre d'appuis en 5s pour déclencher","trigger.scope_hint":"Se déclenche une fois par appui, quel que soit le nombre de récepteurs concernés qui observent le signal.","trigger.save_failed":"Échec de l'enregistrement","common.saving":"Enregistrement...","common.update":"Mettre à jour","common.create":"Créer","common.delete":"Supprimer","assign.heading":"Assigner le signal","assign.hits":"{count} réceptions","assign.mode_existing":"Appareil existant","assign.mode_new":"Nouvel appareil","assign.send_times":"Nombre d'envois","assign.send_times_hint":"Transmet cette commande autant de fois par appui, pour les appareils qui ont besoin d'une répétition. Par défaut 1.","assign.ditto_count":"Nombre de dittos","assign.ditto_title":"Ajoute des trames de répétition après la trame principale ; certains récepteurs stricts en exigent au moins une pour enregistrer la commande.","assign.ditto_hint":"Ajoute des trames de répétition après la trame principale ; certains récepteurs stricts en exigent au moins une pour enregistrer la commande.","assign.assigning":"Assignation...","assign.create_assign":"Créer et assigner","assign.assign":"Assigner","assign.target_device":"Appareil cible","assign.no_devices":'Aucun appareil pour l\'instant. Passez à "Nouvel appareil" pour en créer un.',"assign.select_device":"Sélectionnez un appareil...","assign.command_name":"Nom de la commande","assign.command_placeholder":"Saisissez le nom de la commande","assign.select_command":"Sélectionnez une commande...","assign.custom":"Personnalisé...","assign.command_required":"Le nom de la commande est requis.","assign.target_required":"Sélectionnez un appareil cible.","assign.failed_duplicate":"Échec de l'assignation. Le signal a peut-être un code en double sur l'appareil cible.","pluckdlg.blaster_required":"Choisissez un blaster à cueillir.","pluckdlg.appliance_required":"L'équipement est requis.","pluckdlg.add_heading":"Ajouter un blaster","pluckdlg.loading_blasters":"Chargement des blasters...","pluckdlg.pluck_from":"Cueillir depuis","pluckdlg.select_blaster":"Sélectionnez un blaster","pluckdlg.appliance":"Équipement","pluckdlg.appliance_placeholder":"ex. bougies","pluckdlg.name_placeholder":"ex. Bougies du salon","pluckdlg.signal_heading":"Cueillir un signal","pluckdlg.pluck_failed":"Échec de la cueillette.","pluckdlg.no_response":"Pas de réponse du blaster. Réessayez.","pluckdlg.recognized_as":"Reconnu comme {protocol}","pluckdlg.valid_pronto":"Code Pronto valide","pluckdlg.command_help":"Le nom que vous avez donné à ce code lors de son apprentissage dans l'application du fabricant.","pluckdlg.command_placeholder":"ex. pwr_on","pluckdlg.plucking":"Cueillette...","pluckdlg.pluck":"Cueillir","pluckdlg.captured":"Capturé","pluckdlg.remove_capture":"Retirer cette capture","pluckdlg.alias":"Alias","pluckdlg.no_blasters":"Aucun blaster compatible trouvé. Installez une intégration IR prise en charge (comme Tuya Local) et apprenez d'abord un code.","editor.ditto_disabled_cmd":"Le nombre de dittos s'applique quand la commande est transmise en NEC. Basculez la pastille sur NEC pour l'activer.","editor.ditto_disabled":"Le nombre de dittos s'applique aux signaux décodés (NEC aujourd'hui). Les codes Pronto bruts sont transmis tels que capturés.","editor.copied":"Copié","editor.press_copy":"Appuyez sur Cmd/Ctrl+C","editor.valid":"Code Pronto valide","editor.not_valid":"Pas encore valide","editor.burst_pair.one":"{count} paire de rafales","editor.burst_pair.other":"{count} paires de rafales","editor.recognized_as":"Reconnu comme {protocol}","editor.snap_notice":"La porteuse est à {khz} kHz, hors des standards IR. Certains récepteurs la rejettent.","editor.snapping":"Ajustement...","editor.snap_to":"Ajuster à {khz} kHz","editor.edit_command":"Modifier la commande","editor.edit_signal":"Modifier le signal","editor.create_signal":"Créer un signal","common.save":"Enregistrer","editor.trigger_note_cmd":"Cette commande a un déclencheur qui se re-pointera automatiquement.","editor.trigger_note_sig":"Ce signal a un déclencheur qui se re-pointera automatiquement.","editor.alias_label":"Alias","editor.alias_optional":"Alias (facultatif)","editor.pronto_code":"Code Pronto","editor.select_all":"Tout sélectionner (puis Cmd/Ctrl+C)","editor.alias_placeholder":"ex. Alimentation","editor.send_times_title":"Transmet la commande entière autant de fois comme des appuis indépendants, pour les appareils qui ont besoin d'une répétition.","editor.ditto_title":"Ajoute des trames de répétition après la trame principale. Certains récepteurs stricts, notamment le matériel audio professionnel, en exigent au moins une pour enregistrer la commande.","editor.observed.one":"Observé à la capture : {count} ditto","editor.observed.other":"Observé à la capture : {count} dittos","rel.just_now":"à l'instant","mirror.via":"via {name}","mirror.via_n":"via {count} émetteurs","mirror.not_heard":"pas entendu","mirror.heard_in":"entendu pour la dernière fois dans {areas}","mirror.heard_by":"entendu pour la dernière fois par {names}","mirror.chip_automation":"Envoi d'automatisation","mirror.chip_integration":"Envoi d'intégration","mirror.chip_test":"Envoi de test manuel","mirror.chip_device":"Appareil HAIR","mirror.chip_send":"Envoi","mirror.unknown_title":"Signal IR inconnu envoyé","mirror.unknown_hint":"{name} a émis, mais rien n'était assez proche pour entendre ce qu'il a dit. Placez un récepteur à portée d'oreille pour capter le prochain envoi.","mirror.the_blaster":"Le blaster","mirror.sent":"Envoyé !","mirror.sent_all_n":"Envoyé ! ({sent}/{total})","mirror.sent_partial":"Envoyé ({sent}/{total})","mirror.failed":"Échec","mirror.error":"Erreur","mirror.sending":"Envoi...","mirror.test":"Test","mirror.stat_sends":"ENVOIS","mirror.stat_not_heard":"PAS ENTENDUS","mirror.stat_emitters":"ÉMETTEURS","mirror.stat_signals":"SIGNAUX","mirror.last_send_ago":"dernier envoi il y a {rel}","mirror.last_send_just":"dernier envoi à l'instant","mirror.no_receivers":"aucun récepteur","mirror.filter_all":"Tous ({count})","mirror.filter_not_heard":"Pas entendus ({count})","mirror.search":"Rechercher des envois...","mirror.no_match":"Aucun envoi ne correspond.","mirror.signals.one":"{count} signal","mirror.signals.other":"{count} signaux","mirror.sends_times":"Envoie ce signal {count} fois","mirror.assign_disabled":"Identité inconnue -- rien n'a été entendu en retour à assigner","mirror.assigned_one":"Assigné à {device} / {command}","mirror.assigned_n":"Assigné à {count} commandes :","mirror.assign_title":"Assigner ce signal à un appareil HAIR","mirror.test_title":"Envoyer ce signal via un émetteur pour le tester","mirror.test_disabled":"Identité inconnue -- rien à envoyer","mirror.trigger_disabled":"Identité inconnue -- rien à lier","mirror.trigger_edit":"Modifier le(s) déclencheur(s) de ce signal","mirror.trigger_create":"Se déclenche quand ce signal arrive de l'extérieur de Home Assistant","mirror.delete_title":"Effacer cette entrée (elle revient au prochain envoi)","mirror.empty_title":"Rien d'envoyé pour l'instant","mirror.empty_sub":"Les commandes envoyées par les appareils HAIR, les automatisations ou toute intégration de la plateforme infrarouge apparaîtront ici, avec leur destination et qui les a entendues.","mirror.del_trigger_title":"Supprimer le déclencheur","mirror.del_trigger_msg":"Supprimer définitivement ce déclencheur ? Les automatisations qui l'utilisent cesseront de se déclencher.","mirror.clear_title":"Effacer l'entrée du Mirror","mirror.clear_msg":"Retirer cette entrée du Mirror ? Elle reviendra au prochain envoi de ce signal.","common.delete_failed":"Échec de la suppression : {message}","device_type.other_card":"Appareil IR","devlist.loading":"Chargement des appareils IR...","devlist.empty_title":"Aucun appareil IR pour l'instant","devlist.empty_sub":"Ajoutez votre premier appareil pour commencer.","devlist.add_device_plus":"+ Ajouter un appareil","devlist.title":"Appareils HAIR","devlist.add_device":"Ajouter un appareil","devlist.cmd_badge":"CMD : {count}","devlist.tx_badge":"TX : {count}","devlist.no_tx":"Pas de TX","devlist.rx_native_title":"Reçoit via la plateforme infrarouge native de HA","devlist.rx_bridge_active":"Le pont hérité est toujours actif. Le récepteur natif le remplace -- vous pouvez retirer le bloc on_pronto: de votre configuration ESPHome.","devlist.rx_bridge_title":"Reçoit via l'ancien pont d'événements ESPHome","devlist.rx_upgrade_title":"Passez à HA 2026.6+ pour la prise en charge native des récepteurs","devlist.tx_native_title":"Envoie via la plateforme infrarouge native de HA","devlist.blasters":"Blasters (cueillables)","devlist.emitters":"Émetteurs","devlist.receivers":"Récepteurs","devlist.proxies":"Proxys","devlist.hits_badge":"{count}x réceptions","devlist.on":"ON","devlist.off":"OFF","devlist.delete_trigger":"Supprimer le déclencheur","devlist.delete_device":"Supprimer l'appareil","devlist.open_plucker_title":"Ouvrir dans le Plucker","devlist.open_plucker":"Ouvrir dans le Plucker","devlist.del_trigger_msg":"Retirer \"{name}\" ? L'entité d'événement HA associée sera aussi supprimée.","devlist.del_device_title":"Supprimer l'appareil","devlist.del_device_msg":"Retirer \"{name}\" ? Les commandes, mappages d'action et assignations d'émetteur seront supprimés. Les déclencheurs ne sont pas affectés.","common.close":"Fermer","devdetail.name_updated":"Nom mis à jour","devdetail.type_updated":"Type d'appareil mis à jour","devdetail.emitters_updated":"Émetteurs mis à jour","devdetail.update_failed":"Échec de la mise à jour : {message}","devdetail.reorder_failed":"Échec du réordonnancement : {message}","devdetail.mapped_to":"Mappé sur {action}","devdetail.mapping_cleared":"Mappage effacé","devdetail.mapping_failed":"Échec du mappage : {message}","devdetail.sent_cmd":'"{name}" envoyé',"devdetail.send_failed":"Échec de l'envoi : {message}","devdetail.cmd_updated":"Commande mise à jour","devdetail.cmd_updated_repointed":"Commande mise à jour. Déclencheur {names} re-pointé.","devdetail.rename_failed":"Échec du renommage : {message}","devdetail.removed":'"{name}" retiré',"devdetail.saved":'"{name}" enregistré',"devdetail.type":"Type","devdetail.commands":"Commandes ({count})","devdetail.no_commands":"Aucune commande pour l'instant. Ajoutez-en une ci-dessous.","devdetail.drag":"Glissez pour réordonner","devdetail.map_action":"Mapper une action","devdetail.none_clear":"Aucune (effacer)","devdetail.sniff_title":"Capturer un nouveau signal dans le Sniffer","devdetail.sniffed":"+ Signal sniffé","devdetail.clip_title":"Coller un nouveau signal dans Clips","devdetail.clipped":"+ Signal collé","devdetail.mirror_title":"Surprendre un envoi dans le Mirror","devdetail.mirrored":"+ Signal du Mirror","devdetail.del_device_title":"Supprimer {name} ?","devdetail.del_device_msg":"Cela supprime toutes les commandes capturées et l'entité créée automatiquement. Cette action est irréversible.","devdetail.del_cmd_title":"Supprimer la commande ?","devdetail.del_cmd_msg":'Retirer "{name}" ? Cette action est irréversible.',"devdetail.del_trigger_msg":"Retirer ce déclencheur ? L'entité d'événement HA associée sera aussi supprimée.","rel.min_ago":"il y a {count} min","rel.h_ago":"il y a {count}h","rel.d_ago":"il y a {count}j","sniffer.title":"HAIR Sniffer","sniffer.remotes.one":"{count} télécommande","sniffer.remotes.other":"{count} télécommandes","sniffer.scanning":"Recherche de signaux...","sniffer.empty_title":"Aucun signal inconnu détecté","sniffer.empty_body":"Quand des signaux IR non reconnus sont reçus par vos appareils ESPHome, ils apparaissent ici automatiquement.","sniffer.empty_hint":"Essayez d'appuyer sur un bouton d'une télécommande pas encore configurée.","sniffer.norx_title":"Aucun récepteur IR n'est configuré","sniffer.norx_body":"HAIR n'a encore aucun moyen de recevoir des signaux IR, le Sniffer ne peut donc rien capturer.","sniffer.norx_hint":"Configurez un récepteur ESPHome avec la plateforme infrarouge, ou vérifiez dans Paramètres, puis Appareils et services, que votre appareil IR est bien adopté.","sniffer.show_dismissed_title":"Restaurer des télécommandes précédemment ignorées","sniffer.show_dismissed":"Afficher les ignorées","sniffer.hide_dismissed":"Masquer les ignorées","sniffer.clear_all_title":"Vide tout le catalogue inconnu ET la liste des ignorés. Utilisez Afficher les ignorées avant Tout effacer si vous voulez conserver certaines entrées ignorées.","sniffer.clear_all":"Tout effacer","sniffer.del_signal_title":"Supprimer le signal","sniffer.del_signal_msg":"Supprimer définitivement ce signal ? Cette action est irréversible.","sniffer.clear_all_confirm_title":"Effacer tous les signaux","sniffer.clear_all_confirm_msg":"Supprimer tous les signaux et appareils inconnus ? Cette action est irréversible.","sniffer.hair_device":"Appareil HAIR","sniffer.promote":"Promouvoir","sniffer.dismissed":"ignorée","sniffer.restore":"Restaurer","sniffer.dismiss":"Ignorer","sniffer.addr":"adr : {address}","sniffer.signals_head":"Signaux ({count})","sniffer.first_seen":"Vu pour la première fois : {time}","sniffer.restore_first":"Restaurez d'abord cette télécommande","sniffer.trigger_create":"Créer une entité d'événement HA qui se déclenche sur ce signal","common.raw":"BRUT","sniffer.hit_word.one":"réception","sniffer.hit_word.other":"réceptions","sniffer.signal_word.one":"signal","sniffer.signal_word.other":"signaux","common.loading_plain":"Chargement...","clips.title":"HAIR Clipper","clips.add_remote":"+ Ajouter une télécommande","clips.empty_title":"Aucune télécommande virtuelle pour l'instant","clips.empty_body":"Clipper vous permet de créer des télécommandes en collant des codes Pronto. Créez une télécommande, puis ajoutez un signal pour chaque bouton.","clips.empty_hint":'Cliquez sur "+ Ajouter une télécommande" ci-dessus pour commencer une télécommande collée.',"clips.clear_all_title":"Supprime toutes les télécommandes collées et leurs signaux. Les signaux sniffés ne sont pas touchés.","clips.remote_fallback":"Télécommande","clips.add_signal_title":"Ajouter un signal à cette télécommande","clips.add_signal":"+ Ajouter un signal","clips.no_signals":'Aucun signal pour l\'instant. Cliquez sur "+ Ajouter un signal" pour coller un code Pronto.',"clips.delete_remote_title":"Supprimer cette télécommande et tous ses signaux","clips.delete_remote":"Supprimer la télécommande","clips.test_title":"Envoyer ce signal via un émetteur","clips.clear_all_confirm_title":"Effacer tous les clips","clips.clear_all_confirm_msg":"Supprimer toutes les télécommandes collées et leurs signaux ? Cette action est irréversible. Les signaux sniffés ne sont pas affectés.","clips.del_remote_confirm_title":"Supprimer la télécommande","clips.del_remote_msg_n.one":'Retirer "{name}" et son {count} signal ? Cette action est irréversible.',"clips.del_remote_msg_n.other":'Retirer "{name}" et ses {count} signaux ? Cette action est irréversible.',"clips.del_remote_msg":'Retirer "{name}" ? Cette action est irréversible.',"pluck.vendor_unavailable":"L'intégration de ce blaster n'est pas disponible pour le moment. Vérifiez que l'intégration du fabricant est chargée.","pluck.title":"HAIR Plucker","pluck.add_blaster":"+ Ajouter un blaster","pluck.empty_title":"Aucun blaster cueilli pour l'instant","pluck.empty_body":"Le Plucker importe les codes IR de vos blasters existants pour les utiliser dans HAIR sans tout réapprendre.","pluck.empty_hint":'Cliquez sur "+ Ajouter un blaster" ci-dessus pour refléter un blaster.',"pluck.clear_all_title":"Supprime tous les blasters cueillis et leurs signaux. Les signaux sniffés et collés ne sont pas touchés.","pluck.blaster_fallback":"Blaster","pluck.promote_title":"Créer un appareil HAIR à partir de ce blaster","pluck.pluck_signal_title":"Cueillir un code sur ce blaster","pluck.pluck_signal":"+ Cueillir un signal","pluck.no_signals":'Aucun signal pour l\'instant. Cliquez sur "+ Cueillir un signal" pour extraire un code de ce blaster.',"pluck.delete_blaster_title":"Supprimer ce blaster et tous ses signaux","pluck.delete_blaster":"Supprimer le blaster","pluck.clear_all_confirm_title":"Effacer tous les cueillis","pluck.clear_all_confirm_msg":"Supprimer tous les blasters cueillis et leurs signaux ? Cette action est irréversible. Les signaux sniffés et collés ne sont pas affectés.","pluck.del_blaster_confirm_title":"Supprimer le blaster","devdetail.custom_action":"Personnalisé...","devdetail.custom_action_placeholder":"ex. temp_30","devdetail.set":"Définir","vocab.back_return":"Retour","vocab.brightness_down":"Luminosité -","vocab.brightness_up":"Luminosité +","vocab.channel_down":"Chaîne -","vocab.channel_up":"Chaîne +","vocab.close":"Fermer","vocab.color_temp_cooler":"Blanc plus froid","vocab.color_temp_warmer":"Blanc plus chaud","vocab.down":"Bas","vocab.fan_auto":"Ventilation : Auto","vocab.fan_high":"Ventilation : Forte","vocab.fan_low":"Ventilation : Faible","vocab.fan_medium":"Ventilation : Moyenne","vocab.fast_forward":"Avance rapide","vocab.guide":"Guide","vocab.left":"Gauche","vocab.menu":"Menu","vocab.mode_auto":"Mode : Auto","vocab.mode_cool":"Mode : Froid","vocab.mode_dry":"Mode : Déshumidification","vocab.mode_fan":"Mode : Ventilation","vocab.mode_heat":"Mode : Chauffage","vocab.mute":"Muet","vocab.off":"Arrêt","vocab.on":"Marche","vocab.open":"Ouvrir","vocab.oscillate":"Oscillation","vocab.pause":"Pause","vocab.play":"Lecture","vocab.power":"Alimentation","vocab.power_off":"Éteindre","vocab.power_on":"Allumer","vocab.power_toggle":"Marche/Arrêt","vocab.rewind":"Retour rapide","vocab.right":"Droite","vocab.select_ok":"Sélection/OK","vocab.source_input":"Source/Entrée","vocab.speed_down":"Vitesse -","vocab.speed_up":"Vitesse +","vocab.stop":"Stop","vocab.swing_toggle":"Balayage","vocab.timer":"Minuterie","vocab.up":"Haut","vocab.volume_down":"Volume -","vocab.volume_up":"Volume +"},ja:{"_meta.review":"AI draft (2026-07-19), not yet reviewed by a native speaker -- help wanted, see CONTRIBUTING 'Adding a language'","panel.loading":"読み込み中…","panel.load_failed":"デバイスの読み込みに失敗しました：{message}","panel.open_menu":"メニューを開く","panel.tab.devices":"デバイス","panel.tagline.devices":"IRデバイスと、それを動かすハードウェアを管理します。","panel.tagline.sniffer":"空中を飛ぶIRコードをライブでキャプチャします。","panel.tagline.clips":"既知のIRコードを貼り付けてリモコンを作成します。","panel.tagline.plucker":"既存のブラスターからIRコードを引き抜きます。","panel.tagline.mirror":"Home Assistantの赤外線送信をライブで確認します。","common.confirm":"確認","common.cancel":"キャンセル","common.are_you_sure":"よろしいですか？","common.remove":"削除","alias.placeholder":"この信号のエイリアス","alias.clear":"エイリアスをクリア","alias.edit":"クリックしてエイリアスを編集","alias.name":"クリックしてこの信号に名前を付ける","picker.emitters_label":"IRエミッター","picker.add_emitter":"+ エミッターを追加...","picker.no_emitters":"IRエミッターが見つかりません。","picker.all_emitters_selected":"すべてのエミッターが選択されています。","picker.receivers_label":"経由レシーバー：","picker.add_receiver":"+ レシーバーを追加...","picker.no_receivers":"IRレシーバーが見つかりません。","picker.all_receivers_selected":"すべてのレシーバーが選択されています。","device_type.media_player":"メディアプレーヤー","device_type.ac":"エアコン","device_type.fan":"扇風機","device_type.light":"照明","device_type.switch":"スイッチ","device_type.screen":"スクリーン／シェード","device_type.other":"その他","common.name":"名前","common.device_type":"デバイスタイプ","common.name_required":"名前は必須です。","common.creating":"作成中...","common.device_name_placeholder":"例：リビングのテレビ","promote.heading":"デバイスに昇格","promote.device_name":"デバイス名","promote.device_name_required":"デバイス名は必須です。","promote.emitter_required":"IRエミッターを1つ以上選択してください。","promote.create_device":"デバイスを作成","adddev.heading":"デバイスを追加","adddev.emitter_required":"IRエミッターを1つ以上選んでください。","adddev.create":"作成","dup.heading":"デバイスを複製","dup.hint_duplicating":"{name} を複製しています。","dup.hint_body":"新しいデバイスには、すべてのコマンド、アクションマッピング、エミッター割り当てのコピーが引き継がれます。あとから何でも変更できます。","dup.duplicating":"複製中...","dup.duplicate":"複製","promote.description":"新しいHAIRデバイスを作成します。その後、キャプチャした信号をコマンドとして割り当てられます。","capture.listening":"IR信号を待機中…","capture.instruction":"リモコンをIRレシーバーに向けて「{name}」ボタンを押してください。","capture.remaining":"残り{seconds}秒","capture.captured":"信号をキャプチャしました！","capture.protocol":"プロトコル：{protocol}","capture.protocol_raw":"Raw","capture.verify":"動作しましたか？テストを押して確認してください。","capture.test":"▶ テスト","capture.recapture":"↻ 再キャプチャ","capture.save_next":"保存して次を学習 ▶▶","capture.no_signal":"⚠ 信号が検出されません","capture.tip_point":"リモコンをIRレシーバーに直接向けてください","capture.tip_closer":"近づいてください（1メートル以内）","capture.tip_hold":"ボタンを短く押し続けてください","capture.try_again":"↻ もう一度","capture.duplicate":"⚠ 重複した信号を検出","capture.duplicate_instruction":"この信号は「{name}」コマンドと一致します。複数のボタンで同じ信号を使うリモコンもあります。","capture.recapture_different":"別の信号を再キャプチャ","capture.save_anyway":"そのまま保存","capture.error":"⚠ キャプチャエラー","capture.learning":"学習中：「{name}」","test_emitter.heading":"送信元","test_emitter.sending":"送信中...","test_emitter.send":"送信","createremote.heading":"リモコンを作成","createremote.type":"種類","createremote.blank":"空のリモコン","createremote.from_library":"コードライブラリから","createremote.model":"モデル","createremote.select_model":"モデルを選択","popover.assigned_to":"割り当て先","popover.new_assignment":"+ 新しい割り当て","popover.open_in_devices":"{name} をデバイスタブで開く","popover.triggers":"トリガー","popover.new_trigger":"+ 新しいトリガー","popover.any_receiver":"任意のレシーバー","popover.n_more":"{name} + 他{count}件","cmdrow.rename":"クリックして名前を変更","cmdrow.tx_raw_on":"キャプチャしたProntoを再生します。クリックすると、デコード済みのクリーンなパケットタイミングを送信します。","cmdrow.tx_raw_off":"デコード済みのクリーンなパケットタイミングを送信します。クリックすると、キャプチャしたProntoを再生します。","cmdrow.sends_times":"このコマンドを{count}回送信します","cmdrow.dittos":"NECディットーを{count}個追加します","cmdrow.raw_timings":"RAW：{count}タイミング","cmdrow.not_learned":"未学習","cmdrow.edit_code":"コードを表示・編集","cmdrow.map_action":"アクションマッピングを割り当て","cmdrow.actions":"ACTIONS","cmdrow.test":"テスト","cmdrow.trigger":"トリガー","cmdrow.edit_trigger":"トリガーを編集","cmdrow.create_trigger":"トリガーを作成","cmdrow.delete":"削除","cmdrow.learn":"学習","trigger.alias_tag":"エイリアス","trigger.event":"トリガーイベント","trigger.edit_heading":"トリガーを編集","trigger.create_heading":"トリガーを作成","trigger.mirror_hint":"この信号がHome Assistantの外部（物理リモコンや他のアプリ）から届いたときに発火します。家自身の送信では発火しません。","trigger.name_label":"トリガー名","trigger.name_placeholder":"例：テレビ電源","trigger.min_hits":"最小ヒット数","trigger.min_hits_hint":"発火に必要な5秒以内の押下回数","trigger.scope_hint":"対象のレシーバーがいくつ信号を観測しても、1回の押下につき1回だけ発火します。","trigger.save_failed":"保存に失敗しました","common.saving":"保存中...","common.update":"更新","common.create":"作成","common.delete":"削除","assign.heading":"信号を割り当て","assign.hits":"{count}ヒット","assign.mode_existing":"既存のデバイス","assign.mode_new":"新しいデバイス","assign.send_times":"送信回数","assign.send_times_hint":"リピートが必要なデバイス向けに、1回の押下でこのコマンドをこの回数送信します。デフォルトは1。","assign.ditto_count":"ディットー数","assign.ditto_title":"メインフレームの後にリピートフレームを追加します。厳格なレシーバーでは、コマンドを認識させるのに1つ以上必要な場合があります。","assign.ditto_hint":"メインフレームの後にリピートフレームを追加します。厳格なレシーバーでは、コマンドを認識させるのに1つ以上必要な場合があります。","assign.assigning":"割り当て中...","assign.create_assign":"作成して割り当て","assign.assign":"割り当て","assign.target_device":"対象デバイス","assign.no_devices":"デバイスがまだありません。「新しいデバイス」に切り替えて作成してください。","assign.select_device":"デバイスを選択...","assign.command_name":"コマンド名","assign.command_placeholder":"コマンド名を入力","assign.select_command":"コマンドを選択...","assign.custom":"カスタム...","assign.command_required":"コマンド名は必須です。","assign.target_required":"対象デバイスを選択してください。","assign.failed_duplicate":"割り当てに失敗しました。対象デバイスに重複するコードがある可能性があります。","pluckdlg.blaster_required":"引き抜き元のブラスターを選んでください。","pluckdlg.appliance_required":"対象機器は必須です。","pluckdlg.add_heading":"ブラスターを追加","pluckdlg.loading_blasters":"ブラスターを読み込み中...","pluckdlg.pluck_from":"引き抜き元","pluckdlg.select_blaster":"ブラスターを選択","pluckdlg.appliance":"対象機器","pluckdlg.appliance_placeholder":"例：キャンドル","pluckdlg.name_placeholder":"例：リビングのキャンドル","pluckdlg.signal_heading":"信号を引き抜く","pluckdlg.pluck_failed":"引き抜きに失敗しました。","pluckdlg.no_response":"ブラスターから応答がありません。もう一度お試しください。","pluckdlg.recognized_as":"{protocol} として認識","pluckdlg.valid_pronto":"有効なProntoコード","pluckdlg.command_help":"ベンダーアプリでこのコードを学習したときに付けた名前です。","pluckdlg.command_placeholder":"例：pwr_on","pluckdlg.plucking":"引き抜き中...","pluckdlg.pluck":"引き抜く","pluckdlg.captured":"キャプチャ済み","pluckdlg.remove_capture":"このキャプチャを削除","pluckdlg.alias":"エイリアス","pluckdlg.no_blasters":"互換性のあるブラスターが見つかりません。対応するIR統合（Tuya Localなど）をインストールし、先にコードを学習してください。","editor.ditto_disabled_cmd":"ディットー数は、コマンドがNECとして送信されるときに適用されます。ピルをNECに切り替えると有効になります。","editor.ditto_disabled":"ディットー数はデコード済み信号（現在はNEC）に適用されます。RawのProntoコードはキャプチャどおりに送信されます。","editor.copied":"コピーしました","editor.press_copy":"Cmd/Ctrl+Cを押してください","editor.valid":"有効なProntoコード","editor.not_valid":"まだ有効ではありません","editor.burst_pair.one":"{count}バーストペア","editor.burst_pair.other":"{count}バーストペア","editor.recognized_as":"{protocol} として認識","editor.snap_notice":"キャリアは{khz} kHzで、IR標準から外れています。拒否するレシーバーもあります。","editor.snapping":"スナップ中...","editor.snap_to":"{khz} kHzにスナップ","editor.edit_command":"コマンドを編集","editor.edit_signal":"信号を編集","editor.create_signal":"信号を作成","common.save":"保存","editor.trigger_note_cmd":"このコマンドにはトリガーがあり、自動的に再ポイントされます。","editor.trigger_note_sig":"この信号にはトリガーがあり、自動的に再ポイントされます。","editor.alias_label":"エイリアス","editor.alias_optional":"エイリアス（任意）","editor.pronto_code":"Prontoコード","editor.select_all":"すべて選択（その後Cmd/Ctrl+C）","editor.alias_placeholder":"例：電源","editor.send_times_title":"リピートが必要なデバイス向けに、コマンド全体を独立した押下としてこの回数送信します。","editor.ditto_title":"メインフレームの後にリピートフレームを追加します。業務用オーディオ機器など厳格なレシーバーでは、1つ以上必要な場合があります。","editor.observed.one":"キャプチャ時の観測：ディットー{count}個","editor.observed.other":"キャプチャ時の観測：ディットー{count}個","rel.just_now":"たった今","mirror.via":"{name} 経由","mirror.via_n":"{count}台のエミッター経由","mirror.not_heard":"未受信","mirror.heard_in":"最後に {areas} で受信","mirror.heard_by":"最後に {names} が受信","mirror.chip_automation":"オートメーション送信","mirror.chip_integration":"統合からの送信","mirror.chip_test":"手動テスト送信","mirror.chip_device":"HAIRデバイス","mirror.chip_send":"送信","mirror.unknown_title":"不明なIR信号を送信","mirror.unknown_hint":"{name} が発信しましたが、内容を聞き取れる距離に何もいませんでした。次の送信を捉えるには、レシーバーを聞こえる範囲に置いてください。","mirror.the_blaster":"ブラスター","mirror.sent":"送信しました！","mirror.sent_all_n":"送信しました！（{sent}/{total}）","mirror.sent_partial":"送信（{sent}/{total}）","mirror.failed":"失敗","mirror.error":"エラー","mirror.sending":"送信中...","mirror.test":"テスト","mirror.stat_sends":"送信","mirror.stat_not_heard":"未受信","mirror.stat_emitters":"エミッター","mirror.stat_signals":"信号","mirror.last_send_ago":"最終送信 {rel}前","mirror.last_send_just":"最終送信 たった今","mirror.no_receivers":"レシーバーなし","mirror.filter_all":"すべて（{count}）","mirror.filter_not_heard":"未受信（{count}）","mirror.search":"送信を検索...","mirror.no_match":"一致する送信がありません。","mirror.signals.one":"{count}件の信号","mirror.signals.other":"{count}件の信号","mirror.sends_times":"この信号を{count}回送信します","mirror.assign_disabled":"識別情報不明 -- 割り当てられる受信内容がありません","mirror.assigned_one":"{device} / {command} に割り当て済み","mirror.assigned_n":"{count}件のコマンドに割り当て済み：","mirror.assign_title":"この信号をHAIRデバイスに割り当てる","mirror.test_title":"この信号をエミッターから送信してテストする","mirror.test_disabled":"識別情報不明 -- 送信するものがありません","mirror.trigger_disabled":"識別情報不明 -- バインドするものがありません","mirror.trigger_edit":"この信号のトリガーを編集","mirror.trigger_create":"この信号がHome Assistantの外部から届いたときに発火します","mirror.delete_title":"このエントリをクリア（次回送信時に戻ります）","mirror.empty_title":"まだ何も送信されていません","mirror.empty_sub":"HAIRデバイス、オートメーション、赤外線プラットフォーム上の統合が送信したコマンドが、送信先と受信者の情報とともにここに表示されます。","mirror.del_trigger_title":"トリガーを削除","mirror.del_trigger_msg":"このトリガーを完全に削除しますか？これを使用するオートメーションは発火しなくなります。","mirror.clear_title":"Mirrorのエントリをクリア","mirror.clear_msg":"このエントリをMirrorから削除しますか？この信号が次に送信されると戻ります。","common.delete_failed":"削除に失敗しました：{message}","device_type.other_card":"IRデバイス","devlist.loading":"IRデバイスを読み込み中...","devlist.empty_title":"IRデバイスがまだありません","devlist.empty_sub":"最初のデバイスを追加して始めましょう。","devlist.add_device_plus":"+ デバイスを追加","devlist.title":"HAIRデバイス","devlist.add_device":"デバイスを追加","devlist.cmd_badge":"CMD：{count}","devlist.tx_badge":"TX：{count}","devlist.no_tx":"TXなし","devlist.rx_native_title":"HAのネイティブ赤外線プラットフォーム経由で受信","devlist.rx_bridge_active":"レガシーブリッジがまだ有効です。ネイティブレシーバーが優先されるため、ESPHome設定から on_pronto: ブロックを削除できます。","devlist.rx_bridge_title":"レガシーESPHomeイベントバスブリッジ経由で受信","devlist.rx_upgrade_title":"ネイティブレシーバー対応にはHA 2026.6+へアップグレードしてください","devlist.tx_native_title":"HAのネイティブ赤外線プラットフォーム経由で送信","devlist.blasters":"ブラスター（引き抜き可能）","devlist.emitters":"エミッター","devlist.receivers":"レシーバー","devlist.proxies":"プロキシ","devlist.hits_badge":"{count}回ヒット","devlist.on":"ON","devlist.off":"OFF","devlist.delete_trigger":"トリガーを削除","devlist.delete_device":"デバイスを削除","devlist.open_plucker_title":"Pluckerで開く","devlist.open_plucker":"Pluckerで開く","devlist.del_trigger_msg":"「{name}」を削除しますか？関連するHAイベントエンティティも削除されます。","devlist.del_device_title":"デバイスを削除","devlist.del_device_msg":"「{name}」を削除しますか？コマンド、アクションマッピング、エミッター割り当てが削除されます。トリガーは影響を受けません。","common.close":"閉じる","devdetail.name_updated":"名前を更新しました","devdetail.type_updated":"デバイスタイプを更新しました","devdetail.emitters_updated":"エミッターを更新しました","devdetail.update_failed":"更新に失敗しました：{message}","devdetail.reorder_failed":"並べ替えに失敗しました：{message}","devdetail.mapped_to":"{action} にマッピングしました","devdetail.mapping_cleared":"マッピングをクリアしました","devdetail.mapping_failed":"マッピングに失敗しました：{message}","devdetail.sent_cmd":"「{name}」を送信しました","devdetail.send_failed":"送信に失敗しました：{message}","devdetail.cmd_updated":"コマンドを更新しました","devdetail.cmd_updated_repointed":"コマンドを更新しました。トリガー {names} を再ポイントしました。","devdetail.rename_failed":"名前の変更に失敗しました：{message}","devdetail.removed":"「{name}」を削除しました","devdetail.saved":"「{name}」を保存しました","devdetail.type":"タイプ","devdetail.commands":"コマンド（{count}）","devdetail.no_commands":"コマンドがまだありません。下から追加してください。","devdetail.drag":"ドラッグして並べ替え","devdetail.map_action":"アクションをマッピング","devdetail.none_clear":"なし（クリア）","devdetail.sniff_title":"Snifferで新しい信号をキャプチャ","devdetail.sniffed":"+ スニフした信号","devdetail.clip_title":"Clipsで新しい信号を貼り付け","devdetail.clipped":"+ クリップした信号","devdetail.mirror_title":"Mirrorで送信を傍受","devdetail.mirrored":"+ Mirrorの信号","devdetail.del_device_title":"{name} を削除しますか？","devdetail.del_device_msg":"キャプチャしたすべてのコマンドと自動作成されたエンティティが削除されます。この操作は元に戻せません。","devdetail.del_cmd_title":"コマンドを削除しますか？","devdetail.del_cmd_msg":"「{name}」を削除しますか？元に戻せません。","devdetail.del_trigger_msg":"このトリガーを削除しますか？関連するHAイベントエンティティも削除されます。","rel.min_ago":"{count}分前","rel.h_ago":"{count}時間前","rel.d_ago":"{count}日前","sniffer.title":"HAIR Sniffer","sniffer.remotes.one":"{count}台のリモコン","sniffer.remotes.other":"{count}台のリモコン","sniffer.scanning":"信号をスキャン中...","sniffer.empty_title":"不明な信号は検出されていません","sniffer.empty_body":"ESPHomeデバイスが未認識のIR信号を受信すると、ここに自動的に表示されます。","sniffer.empty_hint":"まだ設定していないリモコンのボタンを押してみてください。","sniffer.norx_title":"IRレシーバーが設定されていません","sniffer.norx_body":"HAIRにはまだIR信号を受信する手段がないため、Snifferは何もキャプチャできません。","sniffer.norx_hint":"赤外線プラットフォームでESPHomeレシーバーを設定するか、設定→デバイスとサービスでIRデバイスが登録済みか確認してください。","sniffer.show_dismissed_title":"非表示にしたリモコンを復元","sniffer.show_dismissed":"非表示を表示","sniffer.hide_dismissed":"非表示を隠す","sniffer.clear_all_title":"不明カタログ全体と非表示リストを消去します。個別の非表示エントリを残したい場合は、「すべてクリア」の前に「非表示を表示」を使ってください。","sniffer.clear_all":"すべてクリア","sniffer.del_signal_title":"信号を削除","sniffer.del_signal_msg":"この信号を完全に削除しますか？元に戻せません。","sniffer.clear_all_confirm_title":"すべての信号をクリア","sniffer.clear_all_confirm_msg":"すべての不明な信号とデバイスを削除しますか？元に戻せません。","sniffer.hair_device":"HAIRデバイス","sniffer.promote":"昇格","sniffer.dismissed":"非表示","sniffer.restore":"復元","sniffer.dismiss":"非表示にする","sniffer.addr":"アドレス：{address}","sniffer.signals_head":"信号（{count}）","sniffer.first_seen":"初回受信：{time}","sniffer.restore_first":"先にこのリモコンを復元してください","sniffer.trigger_create":"この信号で発火するHAイベントエンティティを作成","common.raw":"RAW","sniffer.hit_word.one":"ヒット","sniffer.hit_word.other":"ヒット","sniffer.signal_word.one":"信号","sniffer.signal_word.other":"信号","common.loading_plain":"読み込み中...","clips.title":"HAIR Clipper","clips.add_remote":"+ リモコンを追加","clips.empty_title":"仮想リモコンがまだありません","clips.empty_body":"ClipperはProntoコードを貼り付けてリモコンを作れるツールです。リモコンを作成し、ボタンごとに信号を追加してください。","clips.empty_hint":"上の「+ リモコンを追加」をクリックして、クリップリモコンを始めましょう。","clips.clear_all_title":"クリップしたすべてのリモコンと信号を削除します。スニフした信号は影響を受けません。","clips.remote_fallback":"リモコン","clips.add_signal_title":"このリモコンに信号を追加","clips.add_signal":"+ 信号を追加","clips.no_signals":"信号がまだありません。「+ 信号を追加」をクリックしてProntoコードを貼り付けてください。","clips.delete_remote_title":"このリモコンとすべての信号を削除","clips.delete_remote":"リモコンを削除","clips.test_title":"この信号をエミッターから送信","clips.clear_all_confirm_title":"すべてのクリップをクリア","clips.clear_all_confirm_msg":"クリップしたすべてのリモコンと信号を削除しますか？元に戻せません。スニフした信号は影響を受けません。","clips.del_remote_confirm_title":"リモコンを削除","clips.del_remote_msg_n.one":"「{name}」とその{count}件の信号を削除しますか？元に戻せません。","clips.del_remote_msg_n.other":"「{name}」とその{count}件の信号を削除しますか？元に戻せません。","clips.del_remote_msg":"「{name}」を削除しますか？元に戻せません。","pluck.vendor_unavailable":"このブラスターの統合は現在利用できません。ベンダー統合が読み込まれているか確認してください。","pluck.title":"HAIR Plucker","pluck.add_blaster":"+ ブラスターを追加","pluck.empty_title":"引き抜いたブラスターがまだありません","pluck.empty_body":"Pluckerは既存のブラスターからIRコードをインポートし、1つずつ学習し直さずにHAIRで使えるようにします。","pluck.empty_hint":"上の「+ ブラスターを追加」をクリックしてブラスターをミラーしましょう。","pluck.clear_all_title":"引き抜いたすべてのブラスターと信号を削除します。スニフ・クリップした信号は影響を受けません。","pluck.blaster_fallback":"ブラスター","pluck.promote_title":"このブラスターからHAIRデバイスを作成","pluck.pluck_signal_title":"このブラスターからコードを引き抜く","pluck.pluck_signal":"+ 信号を引き抜く","pluck.no_signals":"信号がまだありません。「+ 信号を引き抜く」をクリックしてこのブラスターからコードを取り出してください。","pluck.delete_blaster_title":"このブラスターとすべての信号を削除","pluck.delete_blaster":"ブラスターを削除","pluck.clear_all_confirm_title":"引き抜いたものをすべてクリア","pluck.clear_all_confirm_msg":"引き抜いたすべてのブラスターと信号を削除しますか？元に戻せません。スニフ・クリップした信号は影響を受けません。","pluck.del_blaster_confirm_title":"ブラスターを削除","devdetail.custom_action":"カスタム...","devdetail.custom_action_placeholder":"例：temp_30","devdetail.set":"設定","vocab.back_return":"戻る","vocab.brightness_down":"明るさ－","vocab.brightness_up":"明るさ＋","vocab.channel_down":"チャンネル－","vocab.channel_up":"チャンネル＋","vocab.close":"閉じる","vocab.color_temp_cooler":"色温度を冷たく","vocab.color_temp_warmer":"色温度を暖かく","vocab.down":"下","vocab.fan_auto":"風量：自動","vocab.fan_high":"風量：強","vocab.fan_low":"風量：弱","vocab.fan_medium":"風量：中","vocab.fast_forward":"早送り","vocab.guide":"番組表","vocab.left":"左","vocab.menu":"メニュー","vocab.mode_auto":"モード：自動","vocab.mode_cool":"モード：冷房","vocab.mode_dry":"モード：除湿","vocab.mode_fan":"モード：送風","vocab.mode_heat":"モード：暖房","vocab.mute":"消音","vocab.off":"オフ","vocab.on":"オン","vocab.open":"開く","vocab.oscillate":"首振り","vocab.pause":"一時停止","vocab.play":"再生","vocab.power":"電源","vocab.power_off":"電源オフ","vocab.power_on":"電源オン","vocab.power_toggle":"電源切替","vocab.rewind":"早戻し","vocab.right":"右","vocab.select_ok":"決定","vocab.source_input":"入力切替","vocab.speed_down":"スピード－","vocab.speed_up":"スピード＋","vocab.stop":"停止","vocab.swing_toggle":"スイング切替","vocab.timer":"タイマー","vocab.up":"上","vocab.volume_down":"音量－","vocab.volume_up":"音量＋"}};let be="en",fe="en",ye=new Intl.PluralRules("en");function xe(){return fe}function $e(e,t){const i=ve[be];let s=i?.[e]??_e[e]??e;if(t)for(const[e,i]of Object.entries(t))s=s.split(`{${e}}`).join(String(i));return s}function we(e){const t=`vocab.${function(e){return e.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/_+/g,"_").replace(/^_+|_+$/g,"")}(e)}`,i=ve[be];return i?.[t]??_e[t]??e}function ke(e,t,i){const s=ye.select(t),r=ve[be],o=`${e}.${s}`,a=`${e}.other`;let n=r?.[o]??r?.[a]??_e[o]??_e[a]??e;if(n=n.split("{count}").join(String(t)),i)for(const[e,t]of Object.entries(i))n=n.split(`{${e}}`).join(String(t));return n}const Ce=e=>(...t)=>({_$litDirective$:e,values:t});let Se=class{constructor(e){}get _$AU(){return this._$AM._$AU}_$AT(e,t,i){this._$Ct=e,this._$AM=t,this._$Ci=i}_$AS(e,t){return this.update(e,t)}update(e,t){return this.render(...t)}};const{I:De}=re,Ae=e=>e,Te=()=>document.createComment(""),Ee=(e,t,i)=>{const s=e._$AA.parentNode,r=void 0===t?e._$AB:t._$AA;if(void 0===i){const t=s.insertBefore(Te(),r),o=s.insertBefore(Te(),r);i=new De(t,o,e,e.options)}else{const t=i._$AB.nextSibling,o=i._$AM,a=o!==e;if(a){let t;i._$AQ?.(e),i._$AM=e,void 0!==i._$AP&&(t=e._$AU)!==o._$AU&&i._$AP(t)}if(t!==r||a){let e=i._$AA;for(;e!==t;){const t=Ae(e).nextSibling;Ae(s).insertBefore(e,r),e=t}}}return i},Ie=(e,t,i=e)=>(e._$AI(t,i),e),Pe={},Re=(e,t=Pe)=>e._$AH=t,Me=e=>{e._$AR(),e._$AA.remove()},He=Ce(class extends Se{constructor(){super(...arguments),this.key=B}render(e,t){return this.key=e,t}update(e,[t,i]){return t!==this.key&&(Re(e),this.key=t),i}}),ze=(e,t,i)=>{const s=new Map;for(let r=t;r<=i;r++)s.set(e[r],r);return s},Ne=Ce(class extends Se{constructor(e){if(super(e),2!==e.type)throw Error("repeat() can only be used in text expressions")}dt(e,t,i){let s;void 0===i?i=t:void 0!==t&&(s=t);const r=[],o=[];let a=0;for(const t of e)r[a]=s?s(t,a):a,o[a]=i(t,a),a++;return{values:o,keys:r}}render(e,t,i){return this.dt(e,t,i).values}update(e,[t,i,s]){const r=(e=>e._$AH)(e),{values:o,keys:a}=this.dt(t,i,s);if(!Array.isArray(r))return this.ut=a,o;const n=this.ut??=[],l=[];let d,c,p=0,h=r.length-1,g=0,m=o.length-1;for(;p<=h&&g<=m;)if(null===r[p])p++;else if(null===r[h])h--;else if(n[p]===a[g])l[g]=Ie(r[p],o[g]),p++,g++;else if(n[h]===a[m])l[m]=Ie(r[h],o[m]),h--,m--;else if(n[p]===a[m])l[m]=Ie(r[p],o[m]),Ee(e,l[m+1],r[p]),p++,m--;else if(n[h]===a[g])l[g]=Ie(r[h],o[g]),Ee(e,r[p],r[h]),h--,g++;else if(void 0===d&&(d=ze(a,g,m),c=ze(n,p,h)),d.has(n[p]))if(d.has(n[h])){const t=c.get(a[g]),i=void 0!==t?r[t]:null;if(null===i){const t=Ee(e,r[p]);Ie(t,o[g]),l[g]=t}else l[g]=Ie(i,o[g]),Ee(e,r[p],i),r[t]=null;g++}else Me(r[h]),h--;else Me(r[p]),p++;for(;g<=m;){const t=Ee(e,l[m+1]);Ie(t,o[g]),l[g++]=t}for(;p<=h;){const e=r[p++];null!==e&&Me(e)}return this.ut=a,Re(e,l),j}});function Le(e,t,i){return(t=function(e){var t=function(e,t){if("object"!=typeof e||!e)return e;var i=e[Symbol.toPrimitive];if(void 0!==i){var s=i.call(e,t);if("object"!=typeof s)return s;throw new TypeError("@@toPrimitive must return a primitive value.")}return String(e)}(e,"string");return"symbol"==typeof t?t:t+""}(t))in e?Object.defineProperty(e,t,{value:i,enumerable:!0,configurable:!0,writable:!0}):e[t]=i,e}function Ve(){return Ve=Object.assign?Object.assign.bind():function(e){for(var t=1;t<arguments.length;t++){var i=arguments[t];for(var s in i)({}).hasOwnProperty.call(i,s)&&(e[s]=i[s])}return e},Ve.apply(null,arguments)}function Oe(e,t){var i=Object.keys(e);if(Object.getOwnPropertySymbols){var s=Object.getOwnPropertySymbols(e);t&&(s=s.filter(function(t){return Object.getOwnPropertyDescriptor(e,t).enumerable})),i.push.apply(i,s)}return i}function qe(e){for(var t=1;t<arguments.length;t++){var i=null!=arguments[t]?arguments[t]:{};t%2?Oe(Object(i),!0).forEach(function(t){Le(e,t,i[t])}):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(i)):Oe(Object(i)).forEach(function(t){Object.defineProperty(e,t,Object.getOwnPropertyDescriptor(i,t))})}return e}function Ue(e){return Ue="function"==typeof Symbol&&"symbol"==typeof Symbol.iterator?function(e){return typeof e}:function(e){return e&&"function"==typeof Symbol&&e.constructor===Symbol&&e!==Symbol.prototype?"symbol":typeof e},Ue(e)}function Fe(e){if("undefined"!=typeof window&&window.navigator)return!!navigator.userAgent.match(e)}var je=Fe(/(?:Trident.*rv[ :]?11\.|msie|iemobile|Windows Phone)/i),Be=Fe(/Edge/i),Xe=Fe(/firefox/i),Ze=Fe(/safari/i)&&!Fe(/chrome/i)&&!Fe(/android/i),We=Fe(/iP(ad|od|hone)/i),Ye=Fe(/chrome/i)&&Fe(/android/i),Ge={capture:!1,passive:!1};function Ke(e,t,i){e.addEventListener(t,i,!je&&Ge)}function Je(e,t,i){e.removeEventListener(t,i,!je&&Ge)}function Qe(e,t){if(t){if(">"===t[0]&&(t=t.substring(1)),e)try{if(e.matches)return e.matches(t);if(e.msMatchesSelector)return e.msMatchesSelector(t);if(e.webkitMatchesSelector)return e.webkitMatchesSelector(t)}catch(e){return!1}return!1}}function et(e){return e.host&&e!==document&&e.host.nodeType&&e.host!==e?e.host:e.parentNode}function tt(e,t,i,s){if(e){i=i||document;do{if(null!=t&&(">"===t[0]?e.parentNode===i&&Qe(e,t):Qe(e,t))||s&&e===i)return e;if(e===i)break}while(e=et(e))}return null}var it,st=/\s+/g;function rt(e,t,i){if(e&&t)if(e.classList)e.classList[i?"add":"remove"](t);else{var s=(" "+e.className+" ").replace(st," ").replace(" "+t+" "," ");e.className=(s+(i?" "+t:"")).replace(st," ")}}function ot(e,t,i){var s=e&&e.style;if(s){if(void 0===i)return document.defaultView&&document.defaultView.getComputedStyle?i=document.defaultView.getComputedStyle(e,""):e.currentStyle&&(i=e.currentStyle),void 0===t?i:i[t];t in s||-1!==t.indexOf("webkit")||(t="-webkit-"+t),s[t]=i+("string"==typeof i?"":"px")}}function at(e,t){var i="";if("string"==typeof e)i=e;else do{var s=ot(e,"transform");s&&"none"!==s&&(i=s+" "+i)}while(!t&&(e=e.parentNode));var r=window.DOMMatrix||window.WebKitCSSMatrix||window.CSSMatrix||window.MSCSSMatrix;return r&&new r(i)}function nt(e,t,i){if(e){var s=e.getElementsByTagName(t),r=0,o=s.length;if(i)for(;r<o;r++)i(s[r],r);return s}return[]}function lt(){return document.scrollingElement||document.documentElement}function dt(e,t,i,s,r){if(e.getBoundingClientRect||e===window){var o,a,n,l,d,c,p;if(e!==window&&e.parentNode&&e!==lt()?(a=(o=e.getBoundingClientRect()).top,n=o.left,l=o.bottom,d=o.right,c=o.height,p=o.width):(a=0,n=0,l=window.innerHeight,d=window.innerWidth,c=window.innerHeight,p=window.innerWidth),(t||i)&&e!==window&&(r=r||e.parentNode,!je))do{if(r&&r.getBoundingClientRect&&("none"!==ot(r,"transform")||i&&"static"!==ot(r,"position"))){var h=r.getBoundingClientRect();a-=h.top+parseInt(ot(r,"border-top-width")),n-=h.left+parseInt(ot(r,"border-left-width")),l=a+o.height,d=n+o.width;break}}while(r=r.parentNode);if(s&&e!==window){var g=at(r||e),m=g&&g.a,u=g&&g.d;g&&(l=(a/=u)+(c/=u),d=(n/=m)+(p/=m))}return{top:a,left:n,bottom:l,right:d,width:p,height:c}}}function ct(e,t,i){for(var s=ut(e,!0),r=dt(e)[t];s;){if(!(r>=dt(s)[i]))return s;if(s===lt())break;s=ut(s,!1)}return!1}function pt(e,t,i,s){for(var r=0,o=0,a=e.children;o<a.length;){if("none"!==a[o].style.display&&a[o]!==bi.ghost&&(s||a[o]!==bi.dragged)&&tt(a[o],i.draggable,e,!1)){if(r===t)return a[o];r++}o++}return null}function ht(e,t){for(var i=e.lastElementChild;i&&(i===bi.ghost||"none"===ot(i,"display")||t&&!Qe(i,t));)i=i.previousElementSibling;return i||null}function gt(e,t){var i=0;if(!e||!e.parentNode)return-1;for(;e=e.previousElementSibling;)"TEMPLATE"===e.nodeName.toUpperCase()||e===bi.clone||t&&!Qe(e,t)||i++;return i}function mt(e){var t=0,i=0,s=lt();if(e)do{var r=at(e),o=r.a,a=r.d;t+=e.scrollLeft*o,i+=e.scrollTop*a}while(e!==s&&(e=e.parentNode));return[t,i]}function ut(e,t){if(!e||!e.getBoundingClientRect)return lt();var i=e,s=!1;do{if(i.clientWidth<i.scrollWidth||i.clientHeight<i.scrollHeight){var r=ot(i);if(i.clientWidth<i.scrollWidth&&("auto"==r.overflowX||"scroll"==r.overflowX)||i.clientHeight<i.scrollHeight&&("auto"==r.overflowY||"scroll"==r.overflowY)){if(!i.getBoundingClientRect||i===document.body)return lt();if(s||t)return i;s=!0}}}while(i=i.parentNode);return lt()}function _t(e,t){return Math.round(e.top)===Math.round(t.top)&&Math.round(e.left)===Math.round(t.left)&&Math.round(e.height)===Math.round(t.height)&&Math.round(e.width)===Math.round(t.width)}function vt(e,t){return function(){if(!it){var i=arguments;1===i.length?e.call(this,i[0]):e.apply(this,i),it=setTimeout(function(){it=void 0},t)}}}function bt(e,t,i){e.scrollLeft+=t,e.scrollTop+=i}function ft(e){var t=window.Polymer,i=window.jQuery||window.Zepto;return t&&t.dom?t.dom(e).cloneNode(!0):i?i(e).clone(!0)[0]:e.cloneNode(!0)}function yt(e,t,i){var s={};return Array.from(e.children).forEach(function(r){var o,a,n,l;if(tt(r,t.draggable,e,!1)&&!r.animated&&r!==i){var d=dt(r);s.left=Math.min(null!==(o=s.left)&&void 0!==o?o:1/0,d.left),s.top=Math.min(null!==(a=s.top)&&void 0!==a?a:1/0,d.top),s.right=Math.max(null!==(n=s.right)&&void 0!==n?n:-1/0,d.right),s.bottom=Math.max(null!==(l=s.bottom)&&void 0!==l?l:-1/0,d.bottom)}}),s.width=s.right-s.left,s.height=s.bottom-s.top,s.x=s.left,s.y=s.top,s}var xt="Sortable"+(new Date).getTime();var $t=[],wt={initializeByDefault:!0},kt={mount:function(e){for(var t in wt)wt.hasOwnProperty(t)&&!(t in e)&&(e[t]=wt[t]);$t.forEach(function(t){if(t.pluginName===e.pluginName)throw"Sortable: Cannot mount plugin ".concat(e.pluginName," more than once")}),$t.push(e)},pluginEvent:function(e,t,i){var s=this;this.eventCanceled=!1,i.cancel=function(){s.eventCanceled=!0};var r=e+"Global";$t.forEach(function(s){t[s.pluginName]&&(t[s.pluginName][r]&&t[s.pluginName][r](qe({sortable:t},i)),t.options[s.pluginName]&&t[s.pluginName][e]&&t[s.pluginName][e](qe({sortable:t},i)))})},initializePlugins:function(e,t,i,s){for(var r in $t.forEach(function(s){var r=s.pluginName;if(e.options[r]||s.initializeByDefault){var o=new s(e,t,e.options);o.sortable=e,o.options=e.options,e[r]=o,Ve(i,o.defaults)}}),e.options)if(e.options.hasOwnProperty(r)){var o=this.modifyOption(e,r,e.options[r]);void 0!==o&&(e.options[r]=o)}},getEventProperties:function(e,t){var i={};return $t.forEach(function(s){"function"==typeof s.eventProperties&&Ve(i,s.eventProperties.call(t[s.pluginName],e))}),i},modifyOption:function(e,t,i){var s;return $t.forEach(function(r){e[r.pluginName]&&r.optionListeners&&"function"==typeof r.optionListeners[t]&&(s=r.optionListeners[t].call(e[r.pluginName],i))}),s}},Ct=["evt"],St=function(e,t){var i=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},s=i.evt,r=function(e,t){if(null==e)return{};var i,s,r=function(e,t){if(null==e)return{};var i={};for(var s in e)if({}.hasOwnProperty.call(e,s)){if(-1!==t.indexOf(s))continue;i[s]=e[s]}return i}(e,t);if(Object.getOwnPropertySymbols){var o=Object.getOwnPropertySymbols(e);for(s=0;s<o.length;s++)i=o[s],-1===t.indexOf(i)&&{}.propertyIsEnumerable.call(e,i)&&(r[i]=e[i])}return r}(i,Ct);kt.pluginEvent.bind(bi)(e,t,qe({dragEl:At,parentEl:Tt,ghostEl:Et,rootEl:It,nextEl:Pt,lastDownEl:Rt,cloneEl:Mt,cloneHidden:Ht,dragStarted:Wt,putSortable:qt,activeSortable:bi.active,originalEvent:s,oldIndex:zt,oldDraggableIndex:Lt,newIndex:Nt,newDraggableIndex:Vt,hideGhostForTarget:mi,unhideGhostForTarget:ui,cloneNowHidden:function(){Ht=!0},cloneNowShown:function(){Ht=!1},dispatchSortableEvent:function(e){Dt({sortable:t,name:e,originalEvent:s})}},r))};function Dt(e){!function(e){var t=e.sortable,i=e.rootEl,s=e.name,r=e.targetEl,o=e.cloneEl,a=e.toEl,n=e.fromEl,l=e.oldIndex,d=e.newIndex,c=e.oldDraggableIndex,p=e.newDraggableIndex,h=e.originalEvent,g=e.putSortable,m=e.extraEventProperties;if(t=t||i&&i[xt]){var u,_=t.options,v="on"+s.charAt(0).toUpperCase()+s.substr(1);!window.CustomEvent||je||Be?(u=document.createEvent("Event")).initEvent(s,!0,!0):u=new CustomEvent(s,{bubbles:!0,cancelable:!0}),u.to=a||i,u.from=n||i,u.item=r||i,u.clone=o,u.oldIndex=l,u.newIndex=d,u.oldDraggableIndex=c,u.newDraggableIndex=p,u.originalEvent=h,u.pullMode=g?g.lastPutMode:void 0;var b=qe(qe({},m),kt.getEventProperties(s,t));for(var f in b)u[f]=b[f];i&&i.dispatchEvent(u),_[v]&&_[v].call(t,u)}}(qe({putSortable:qt,cloneEl:Mt,targetEl:At,rootEl:It,oldIndex:zt,oldDraggableIndex:Lt,newIndex:Nt,newDraggableIndex:Vt},e))}var At,Tt,Et,It,Pt,Rt,Mt,Ht,zt,Nt,Lt,Vt,Ot,qt,Ut,Ft,jt,Bt,Xt,Zt,Wt,Yt,Gt,Kt,Jt,Qt=!1,ei=!1,ti=[],ii=!1,si=!1,ri=[],oi=!1,ai=[],ni="undefined"!=typeof document,li=We,di=Be||je?"cssFloat":"float",ci=ni&&!Ye&&!We&&"draggable"in document.createElement("div"),pi=function(){if(ni){if(je)return!1;var e=document.createElement("x");return e.style.cssText="pointer-events:auto","auto"===e.style.pointerEvents}}(),hi=function(e,t){var i=ot(e),s=parseInt(i.width)-parseInt(i.paddingLeft)-parseInt(i.paddingRight)-parseInt(i.borderLeftWidth)-parseInt(i.borderRightWidth),r=pt(e,0,t),o=pt(e,1,t),a=r&&ot(r),n=o&&ot(o),l=a&&parseInt(a.marginLeft)+parseInt(a.marginRight)+dt(r).width,d=n&&parseInt(n.marginLeft)+parseInt(n.marginRight)+dt(o).width;if("flex"===i.display)return"column"===i.flexDirection||"column-reverse"===i.flexDirection?"vertical":"horizontal";if("grid"===i.display)return i.gridTemplateColumns.split(" ").length<=1?"vertical":"horizontal";if(r&&a.float&&"none"!==a.float){var c="left"===a.float?"left":"right";return!o||"both"!==n.clear&&n.clear!==c?"horizontal":"vertical"}return r&&("block"===a.display||"flex"===a.display||"table"===a.display||"grid"===a.display||l>=s&&"none"===i[di]||o&&"none"===i[di]&&l+d>s)?"vertical":"horizontal"},gi=function(e){function t(e,i){return function(s,r,o,a){var n=s.options.group.name&&r.options.group.name&&s.options.group.name===r.options.group.name;if(null==e&&(i||n))return!0;if(null==e||!1===e)return!1;if(i&&"clone"===e)return e;if("function"==typeof e)return t(e(s,r,o,a),i)(s,r,o,a);var l=(i?s:r).options.group.name;return!0===e||"string"==typeof e&&e===l||e.join&&e.indexOf(l)>-1}}var i={},s=e.group;s&&"object"==Ue(s)||(s={name:s}),i.name=s.name,i.checkPull=t(s.pull,!0),i.checkPut=t(s.put),i.revertClone=s.revertClone,e.group=i},mi=function(){!pi&&Et&&ot(Et,"display","none")},ui=function(){!pi&&Et&&ot(Et,"display","")};ni&&!Ye&&document.addEventListener("click",function(e){if(ei)return e.preventDefault(),e.stopPropagation&&e.stopPropagation(),e.stopImmediatePropagation&&e.stopImmediatePropagation(),ei=!1,!1},!0);var _i=function(e){if(At){var t=function(e,t){var i;return ti.some(function(s){var r=s[xt].options.emptyInsertThreshold;if(r&&!ht(s)){var o=dt(s),a=e>=o.left-r&&e<=o.right+r,n=t>=o.top-r&&t<=o.bottom+r;return a&&n?i=s:void 0}}),i}((e=e.touches?e.touches[0]:e).clientX,e.clientY);if(t){var i={};for(var s in e)e.hasOwnProperty(s)&&(i[s]=e[s]);i.target=i.rootEl=t,i.preventDefault=void 0,i.stopPropagation=void 0,t[xt]._onDragOver(i)}}},vi=function(e){At&&At.parentNode[xt]._isOutsideThisEl(e.target)};function bi(e,t){if(!e||!e.nodeType||1!==e.nodeType)throw"Sortable: `el` must be an HTMLElement, not ".concat({}.toString.call(e));this.el=e,this.options=t=Ve({},t),e[xt]=this;var i,s,r={group:null,sort:!0,disabled:!1,store:null,handle:null,draggable:/^[uo]l$/i.test(e.nodeName)?">li":">*",swapThreshold:1,invertSwap:!1,invertedSwapThreshold:null,removeCloneOnHide:!0,direction:function(){return hi(e,this.options)},ghostClass:"sortable-ghost",chosenClass:"sortable-chosen",dragClass:"sortable-drag",ignore:"a, img",filter:null,preventOnFilter:!0,animation:0,easing:null,setData:function(e,t){e.setData("Text",t.textContent)},dropBubble:!1,dragoverBubble:!1,dataIdAttr:"data-id",delay:0,delayOnTouchOnly:!1,touchStartThreshold:(Number.parseInt?Number:window).parseInt(window.devicePixelRatio,10)||1,forceFallback:!1,fallbackClass:"sortable-fallback",fallbackOnBody:!1,fallbackTolerance:0,fallbackOffset:{x:0,y:0},supportPointer:!1!==bi.supportPointer&&"PointerEvent"in window&&(!Ze||We),emptyInsertThreshold:5};for(var o in kt.initializePlugins(this,e,r),r)!(o in t)&&(t[o]=r[o]);for(var a in gi(t),this)"_"===a.charAt(0)&&"function"==typeof this[a]&&(this[a]=this[a].bind(this));this.nativeDraggable=!t.forceFallback&&ci,this.nativeDraggable&&(this.options.touchStartThreshold=1),t.supportPointer?Ke(e,"pointerdown",this._onTapStart):(Ke(e,"mousedown",this._onTapStart),Ke(e,"touchstart",this._onTapStart)),this.nativeDraggable&&(Ke(e,"dragover",this),Ke(e,"dragenter",this)),ti.push(this.el),t.store&&t.store.get&&this.sort(t.store.get(this)||[]),Ve(this,(s=[],{captureAnimationState:function(){s=[],this.options.animation&&[].slice.call(this.el.children).forEach(function(e){if("none"!==ot(e,"display")&&e!==bi.ghost){s.push({target:e,rect:dt(e)});var t=qe({},s[s.length-1].rect);if(e.thisAnimationDuration){var i=at(e,!0);i&&(t.top-=i.f,t.left-=i.e)}e.fromRect=t}})},addAnimationState:function(e){s.push(e)},removeAnimationState:function(e){s.splice(function(e,t){for(var i in e)if(e.hasOwnProperty(i))for(var s in t)if(t.hasOwnProperty(s)&&t[s]===e[i][s])return Number(i);return-1}(s,{target:e}),1)},animateAll:function(e){var t=this;if(!this.options.animation)return clearTimeout(i),void("function"==typeof e&&e());var r=!1,o=0;s.forEach(function(e){var i=0,s=e.target,a=s.fromRect,n=dt(s),l=s.prevFromRect,d=s.prevToRect,c=e.rect,p=at(s,!0);p&&(n.top-=p.f,n.left-=p.e),s.toRect=n,s.thisAnimationDuration&&_t(l,n)&&!_t(a,n)&&(c.top-n.top)/(c.left-n.left)===(a.top-n.top)/(a.left-n.left)&&(i=function(e,t,i,s){return Math.sqrt(Math.pow(t.top-e.top,2)+Math.pow(t.left-e.left,2))/Math.sqrt(Math.pow(t.top-i.top,2)+Math.pow(t.left-i.left,2))*s.animation}(c,l,d,t.options)),_t(n,a)||(s.prevFromRect=a,s.prevToRect=n,i||(i=t.options.animation),t.animate(s,c,n,i)),i&&(r=!0,o=Math.max(o,i),clearTimeout(s.animationResetTimer),s.animationResetTimer=setTimeout(function(){s.animationTime=0,s.prevFromRect=null,s.fromRect=null,s.prevToRect=null,s.thisAnimationDuration=null},i),s.thisAnimationDuration=i)}),clearTimeout(i),r?i=setTimeout(function(){"function"==typeof e&&e()},o):"function"==typeof e&&e(),s=[]},animate:function(e,t,i,s){if(s){ot(e,"transition",""),ot(e,"transform","");var r=at(this.el),o=r&&r.a,a=r&&r.d,n=(t.left-i.left)/(o||1),l=(t.top-i.top)/(a||1);e.animatingX=!!n,e.animatingY=!!l,ot(e,"transform","translate3d("+n+"px,"+l+"px,0)"),this.forRepaintDummy=function(e){return e.offsetWidth}(e),ot(e,"transition","transform "+s+"ms"+(this.options.easing?" "+this.options.easing:"")),ot(e,"transform","translate3d(0,0,0)"),"number"==typeof e.animated&&clearTimeout(e.animated),e.animated=setTimeout(function(){ot(e,"transition",""),ot(e,"transform",""),e.animated=!1,e.animatingX=!1,e.animatingY=!1},s)}}}))}function fi(e,t,i,s,r,o,a,n){var l,d,c=e[xt],p=c.options.onMove;return!window.CustomEvent||je||Be?(l=document.createEvent("Event")).initEvent("move",!0,!0):l=new CustomEvent("move",{bubbles:!0,cancelable:!0}),l.to=t,l.from=e,l.dragged=i,l.draggedRect=s,l.related=r||t,l.relatedRect=o||dt(t),l.willInsertAfter=n,l.originalEvent=a,e.dispatchEvent(l),p&&(d=p.call(c,l,a)),d}function yi(e){e.draggable=!1}function xi(){oi=!1}function $i(e){for(var t=e.tagName+e.className+e.src+e.href+e.textContent,i=t.length,s=0;i--;)s+=t.charCodeAt(i);return s.toString(36)}function wi(e){return setTimeout(e,0)}function ki(e){return clearTimeout(e)}bi.prototype={constructor:bi,_isOutsideThisEl:function(e){this.el.contains(e)||e===this.el||(Yt=null)},_getDirection:function(e,t){return"function"==typeof this.options.direction?this.options.direction.call(this,e,t,At):this.options.direction},_onTapStart:function(e){if(e.cancelable){var t=this,i=this.el,s=this.options,r=s.preventOnFilter,o=e.type,a=e.touches&&e.touches[0]||e.pointerType&&"touch"===e.pointerType&&e,n=(a||e).target,l=e.target.shadowRoot&&(e.path&&e.path[0]||e.composedPath&&e.composedPath()[0])||n,d=s.filter;if(function(e){ai.length=0;for(var t=e.getElementsByTagName("input"),i=t.length;i--;){var s=t[i];s.checked&&ai.push(s)}}(i),!At&&!(/mousedown|pointerdown/.test(o)&&0!==e.button||s.disabled)&&!l.isContentEditable&&(this.nativeDraggable||!Ze||!n||"SELECT"!==n.tagName.toUpperCase())&&!((n=tt(n,s.draggable,i,!1))&&n.animated||Rt===n)){if(zt=gt(n),Lt=gt(n,s.draggable),"function"==typeof d){if(d.call(this,e,n,this))return Dt({sortable:t,rootEl:l,name:"filter",targetEl:n,toEl:i,fromEl:i}),St("filter",t,{evt:e}),void(r&&e.preventDefault())}else if(d&&(d=d.split(",").some(function(s){if(s=tt(l,s.trim(),i,!1))return Dt({sortable:t,rootEl:s,name:"filter",targetEl:n,fromEl:i,toEl:i}),St("filter",t,{evt:e}),!0})))return void(r&&e.preventDefault());s.handle&&!tt(l,s.handle,i,!1)||this._prepareDragStart(e,a,n)}}},_prepareDragStart:function(e,t,i){var s,r=this,o=r.el,a=r.options,n=o.ownerDocument;if(i&&!At&&i.parentNode===o){var l=dt(i);if(It=o,Tt=(At=i).parentNode,Pt=At.nextSibling,Rt=i,Ot=a.group,bi.dragged=At,Ut={target:At,clientX:(t||e).clientX,clientY:(t||e).clientY},Xt=Ut.clientX-l.left,Zt=Ut.clientY-l.top,this._lastX=(t||e).clientX,this._lastY=(t||e).clientY,At.style["will-change"]="all",s=function(){St("delayEnded",r,{evt:e}),bi.eventCanceled?r._onDrop():(r._disableDelayedDragEvents(),!Xe&&r.nativeDraggable&&(At.draggable=!0),r._triggerDragStart(e,t),Dt({sortable:r,name:"choose",originalEvent:e}),rt(At,a.chosenClass,!0))},a.ignore.split(",").forEach(function(e){nt(At,e.trim(),yi)}),Ke(n,"dragover",_i),Ke(n,"mousemove",_i),Ke(n,"touchmove",_i),a.supportPointer?(Ke(n,"pointerup",r._onDrop),!this.nativeDraggable&&Ke(n,"pointercancel",r._onDrop)):(Ke(n,"mouseup",r._onDrop),Ke(n,"touchend",r._onDrop),Ke(n,"touchcancel",r._onDrop)),Xe&&this.nativeDraggable&&(this.options.touchStartThreshold=4,At.draggable=!0),St("delayStart",this,{evt:e}),!a.delay||a.delayOnTouchOnly&&!t||this.nativeDraggable&&(Be||je))s();else{if(bi.eventCanceled)return void this._onDrop();a.supportPointer?(Ke(n,"pointerup",r._disableDelayedDrag),Ke(n,"pointercancel",r._disableDelayedDrag)):(Ke(n,"mouseup",r._disableDelayedDrag),Ke(n,"touchend",r._disableDelayedDrag),Ke(n,"touchcancel",r._disableDelayedDrag)),Ke(n,"mousemove",r._delayedDragTouchMoveHandler),Ke(n,"touchmove",r._delayedDragTouchMoveHandler),a.supportPointer&&Ke(n,"pointermove",r._delayedDragTouchMoveHandler),r._dragStartTimer=setTimeout(s,a.delay)}}},_delayedDragTouchMoveHandler:function(e){var t=e.touches?e.touches[0]:e;Math.max(Math.abs(t.clientX-this._lastX),Math.abs(t.clientY-this._lastY))>=Math.floor(this.options.touchStartThreshold/(this.nativeDraggable&&window.devicePixelRatio||1))&&this._disableDelayedDrag()},_disableDelayedDrag:function(){At&&yi(At),clearTimeout(this._dragStartTimer),this._disableDelayedDragEvents()},_disableDelayedDragEvents:function(){var e=this.el.ownerDocument;Je(e,"mouseup",this._disableDelayedDrag),Je(e,"touchend",this._disableDelayedDrag),Je(e,"touchcancel",this._disableDelayedDrag),Je(e,"pointerup",this._disableDelayedDrag),Je(e,"pointercancel",this._disableDelayedDrag),Je(e,"mousemove",this._delayedDragTouchMoveHandler),Je(e,"touchmove",this._delayedDragTouchMoveHandler),Je(e,"pointermove",this._delayedDragTouchMoveHandler)},_triggerDragStart:function(e,t){t=t||"touch"==e.pointerType&&e,!this.nativeDraggable||t?this.options.supportPointer?Ke(document,"pointermove",this._onTouchMove):Ke(document,t?"touchmove":"mousemove",this._onTouchMove):(Ke(At,"dragend",this),Ke(It,"dragstart",this._onDragStart));try{document.selection?wi(function(){document.selection.empty()}):window.getSelection().removeAllRanges()}catch(e){}},_dragStarted:function(e,t){if(Qt=!1,It&&At){St("dragStarted",this,{evt:t}),this.nativeDraggable&&Ke(document,"dragover",vi);var i=this.options;!e&&rt(At,i.dragClass,!1),rt(At,i.ghostClass,!0),bi.active=this,e&&this._appendGhost(),Dt({sortable:this,name:"start",originalEvent:t})}else this._nulling()},_emulateDragOver:function(){if(Ft){this._lastX=Ft.clientX,this._lastY=Ft.clientY,mi();for(var e=document.elementFromPoint(Ft.clientX,Ft.clientY),t=e;e&&e.shadowRoot&&(e=e.shadowRoot.elementFromPoint(Ft.clientX,Ft.clientY))!==t;)t=e;if(At.parentNode[xt]._isOutsideThisEl(e),t)do{if(t[xt]&&t[xt]._onDragOver({clientX:Ft.clientX,clientY:Ft.clientY,target:e,rootEl:t})&&!this.options.dragoverBubble)break;e=t}while(t=et(t));ui()}},_onTouchMove:function(e){if(Ut){var t=this.options,i=t.fallbackTolerance,s=t.fallbackOffset,r=e.touches?e.touches[0]:e,o=Et&&at(Et,!0),a=Et&&o&&o.a,n=Et&&o&&o.d,l=li&&Jt&&mt(Jt),d=(r.clientX-Ut.clientX+s.x)/(a||1)+(l?l[0]-ri[0]:0)/(a||1),c=(r.clientY-Ut.clientY+s.y)/(n||1)+(l?l[1]-ri[1]:0)/(n||1);if(!bi.active&&!Qt){if(i&&Math.max(Math.abs(r.clientX-this._lastX),Math.abs(r.clientY-this._lastY))<i)return;this._onDragStart(e,!0)}if(Et){o?(o.e+=d-(jt||0),o.f+=c-(Bt||0)):o={a:1,b:0,c:0,d:1,e:d,f:c};var p="matrix(".concat(o.a,",").concat(o.b,",").concat(o.c,",").concat(o.d,",").concat(o.e,",").concat(o.f,")");ot(Et,"webkitTransform",p),ot(Et,"mozTransform",p),ot(Et,"msTransform",p),ot(Et,"transform",p),jt=d,Bt=c,Ft=r}e.cancelable&&e.preventDefault()}},_appendGhost:function(){if(!Et){var e=this.options.fallbackOnBody?document.body:It,t=dt(At,!0,li,!0,e),i=this.options;if(li){for(Jt=e;"static"===ot(Jt,"position")&&"none"===ot(Jt,"transform")&&Jt!==document;)Jt=Jt.parentNode;Jt!==document.body&&Jt!==document.documentElement?(Jt===document&&(Jt=lt()),t.top+=Jt.scrollTop,t.left+=Jt.scrollLeft):Jt=lt(),ri=mt(Jt)}rt(Et=At.cloneNode(!0),i.ghostClass,!1),rt(Et,i.fallbackClass,!0),rt(Et,i.dragClass,!0),ot(Et,"transition",""),ot(Et,"transform",""),ot(Et,"box-sizing","border-box"),ot(Et,"margin",0),ot(Et,"top",t.top),ot(Et,"left",t.left),ot(Et,"width",t.width),ot(Et,"height",t.height),ot(Et,"opacity","0.8"),ot(Et,"position",li?"absolute":"fixed"),ot(Et,"zIndex","100000"),ot(Et,"pointerEvents","none"),bi.ghost=Et,e.appendChild(Et),ot(Et,"transform-origin",Xt/parseInt(Et.style.width)*100+"% "+Zt/parseInt(Et.style.height)*100+"%")}},_onDragStart:function(e,t){var i=this,s=e.dataTransfer,r=i.options;St("dragStart",this,{evt:e}),bi.eventCanceled?this._onDrop():(St("setupClone",this),bi.eventCanceled||((Mt=ft(At)).removeAttribute("id"),Mt.draggable=!1,Mt.style["will-change"]="",this._hideClone(),rt(Mt,this.options.chosenClass,!1),bi.clone=Mt),i.cloneId=wi(function(){St("clone",i),bi.eventCanceled||(i.options.removeCloneOnHide||It.insertBefore(Mt,At),i._hideClone(),Dt({sortable:i,name:"clone"}))}),!t&&rt(At,r.dragClass,!0),t?(ei=!0,i._loopId=setInterval(i._emulateDragOver,50)):(Je(document,"mouseup",i._onDrop),Je(document,"touchend",i._onDrop),Je(document,"touchcancel",i._onDrop),s&&(s.effectAllowed="move",r.setData&&r.setData.call(i,s,At)),Ke(document,"drop",i),ot(At,"transform","translateZ(0)")),Qt=!0,i._dragStartId=wi(i._dragStarted.bind(i,t,e)),Ke(document,"selectstart",i),Wt=!0,window.getSelection().removeAllRanges(),Ze&&ot(document.body,"user-select","none"))},_onDragOver:function(e){var t,i,s,r,o=this.el,a=e.target,n=this.options,l=n.group,d=bi.active,c=Ot===l,p=n.sort,h=qt||d,g=this,m=!1;if(!oi){if(void 0!==e.preventDefault&&e.cancelable&&e.preventDefault(),a=tt(a,n.draggable,o,!0),T("dragOver"),bi.eventCanceled)return m;if(At.contains(e.target)||a.animated&&a.animatingX&&a.animatingY||g._ignoreWhileAnimating===a)return I(!1);if(ei=!1,d&&!n.disabled&&(c?p||(s=Tt!==It):qt===this||(this.lastPutMode=Ot.checkPull(this,d,At,e))&&l.checkPut(this,d,At,e))){if(r="vertical"===this._getDirection(e,a),t=dt(At),T("dragOverValid"),bi.eventCanceled)return m;if(s)return Tt=It,E(),this._hideClone(),T("revert"),bi.eventCanceled||(Pt?It.insertBefore(At,Pt):It.appendChild(At)),I(!0);var u=ht(o,n.draggable);if(!u||function(e,t,i){var s=dt(ht(i.el,i.options.draggable)),r=yt(i.el,i.options,Et);return t?e.clientX>r.right+10||e.clientY>s.bottom&&e.clientX>s.left:e.clientY>r.bottom+10||e.clientX>s.right&&e.clientY>s.top}(e,r,this)&&!u.animated){if(u===At)return I(!1);if(u&&o===e.target&&(a=u),a&&(i=dt(a)),!1!==fi(It,o,At,t,a,i,e,!!a))return E(),u&&u.nextSibling?o.insertBefore(At,u.nextSibling):o.appendChild(At),Tt=o,P(),I(!0)}else if(u&&function(e,t,i){var s=dt(pt(i.el,0,i.options,!0)),r=yt(i.el,i.options,Et);return t?e.clientX<r.left-10||e.clientY<s.top&&e.clientX<s.right:e.clientY<r.top-10||e.clientY<s.bottom&&e.clientX<s.left}(e,r,this)){var _=pt(o,0,n,!0);if(_===At)return I(!1);if(i=dt(a=_),!1!==fi(It,o,At,t,a,i,e,!1))return E(),o.insertBefore(At,_),Tt=o,P(),I(!0)}else if(a.parentNode===o){i=dt(a);var v,b,f,y=At.parentNode!==o,x=!function(e,t,i){var s=i?e.left:e.top,r=i?e.right:e.bottom,o=i?e.width:e.height,a=i?t.left:t.top,n=i?t.right:t.bottom,l=i?t.width:t.height;return s===a||r===n||s+o/2===a+l/2}(At.animated&&At.toRect||t,a.animated&&a.toRect||i,r),$=r?"top":"left",w=ct(a,"top","top")||ct(At,"top","top"),k=w?w.scrollTop:void 0;if(Yt!==a&&(b=i[$],ii=!1,si=!x&&n.invertSwap||y),v=function(e,t,i,s,r,o,a,n){var l=s?e.clientY:e.clientX,d=s?i.height:i.width,c=s?i.top:i.left,p=s?i.bottom:i.right,h=!1;if(!a)if(n&&Kt<d*r){if(!ii&&(1===Gt?l>c+d*o/2:l<p-d*o/2)&&(ii=!0),ii)h=!0;else if(1===Gt?l<c+Kt:l>p-Kt)return-Gt}else if(l>c+d*(1-r)/2&&l<p-d*(1-r)/2)return function(e){return gt(At)<gt(e)?1:-1}(t);return(h=h||a)&&(l<c+d*o/2||l>p-d*o/2)?l>c+d/2?1:-1:0}(e,a,i,r,x?1:n.swapThreshold,null==n.invertedSwapThreshold?n.swapThreshold:n.invertedSwapThreshold,si,Yt===a),0!==v){var C=gt(At);do{C-=v,f=Tt.children[C]}while(f&&("none"===ot(f,"display")||f===Et))}if(0===v||f===a)return I(!1);Yt=a,Gt=v;var S=a.nextElementSibling,D=!1,A=fi(It,o,At,t,a,i,e,D=1===v);if(!1!==A)return 1!==A&&-1!==A||(D=1===A),oi=!0,setTimeout(xi,30),E(),D&&!S?o.appendChild(At):a.parentNode.insertBefore(At,D?S:a),w&&bt(w,0,k-w.scrollTop),Tt=At.parentNode,void 0===b||si||(Kt=Math.abs(b-dt(a)[$])),P(),I(!0)}if(o.contains(At))return I(!1)}return!1}function T(n,l){St(n,g,qe({evt:e,isOwner:c,axis:r?"vertical":"horizontal",revert:s,dragRect:t,targetRect:i,canSort:p,fromSortable:h,target:a,completed:I,onMove:function(i,s){return fi(It,o,At,t,i,dt(i),e,s)},changed:P},l))}function E(){T("dragOverAnimationCapture"),g.captureAnimationState(),g!==h&&h.captureAnimationState()}function I(t){return T("dragOverCompleted",{insertion:t}),t&&(c?d._hideClone():d._showClone(g),g!==h&&(rt(At,qt?qt.options.ghostClass:d.options.ghostClass,!1),rt(At,n.ghostClass,!0)),qt!==g&&g!==bi.active?qt=g:g===bi.active&&qt&&(qt=null),h===g&&(g._ignoreWhileAnimating=a),g.animateAll(function(){T("dragOverAnimationComplete"),g._ignoreWhileAnimating=null}),g!==h&&(h.animateAll(),h._ignoreWhileAnimating=null)),(a===At&&!At.animated||a===o&&!a.animated)&&(Yt=null),n.dragoverBubble||e.rootEl||a===document||(At.parentNode[xt]._isOutsideThisEl(e.target),!t&&_i(e)),!n.dragoverBubble&&e.stopPropagation&&e.stopPropagation(),m=!0}function P(){Nt=gt(At),Vt=gt(At,n.draggable),Dt({sortable:g,name:"change",toEl:o,newIndex:Nt,newDraggableIndex:Vt,originalEvent:e})}},_ignoreWhileAnimating:null,_offMoveEvents:function(){Je(document,"mousemove",this._onTouchMove),Je(document,"touchmove",this._onTouchMove),Je(document,"pointermove",this._onTouchMove),Je(document,"dragover",_i),Je(document,"mousemove",_i),Je(document,"touchmove",_i)},_offUpEvents:function(){var e=this.el.ownerDocument;Je(e,"mouseup",this._onDrop),Je(e,"touchend",this._onDrop),Je(e,"pointerup",this._onDrop),Je(e,"pointercancel",this._onDrop),Je(e,"touchcancel",this._onDrop),Je(document,"selectstart",this)},_onDrop:function(e){var t=this.el,i=this.options;Nt=gt(At),Vt=gt(At,i.draggable),St("drop",this,{evt:e}),Tt=At&&At.parentNode,Nt=gt(At),Vt=gt(At,i.draggable),bi.eventCanceled||(Qt=!1,si=!1,ii=!1,clearInterval(this._loopId),clearTimeout(this._dragStartTimer),ki(this.cloneId),ki(this._dragStartId),this.nativeDraggable&&(Je(document,"drop",this),Je(t,"dragstart",this._onDragStart)),this._offMoveEvents(),this._offUpEvents(),Ze&&ot(document.body,"user-select",""),ot(At,"transform",""),e&&(Wt&&(e.cancelable&&e.preventDefault(),!i.dropBubble&&e.stopPropagation()),Et&&Et.parentNode&&Et.parentNode.removeChild(Et),(It===Tt||qt&&"clone"!==qt.lastPutMode)&&Mt&&Mt.parentNode&&Mt.parentNode.removeChild(Mt),At&&(this.nativeDraggable&&Je(At,"dragend",this),yi(At),At.style["will-change"]="",Wt&&!Qt&&rt(At,qt?qt.options.ghostClass:this.options.ghostClass,!1),rt(At,this.options.chosenClass,!1),Dt({sortable:this,name:"unchoose",toEl:Tt,newIndex:null,newDraggableIndex:null,originalEvent:e}),It!==Tt?(Nt>=0&&(Dt({rootEl:Tt,name:"add",toEl:Tt,fromEl:It,originalEvent:e}),Dt({sortable:this,name:"remove",toEl:Tt,originalEvent:e}),Dt({rootEl:Tt,name:"sort",toEl:Tt,fromEl:It,originalEvent:e}),Dt({sortable:this,name:"sort",toEl:Tt,originalEvent:e})),qt&&qt.save()):Nt!==zt&&Nt>=0&&(Dt({sortable:this,name:"update",toEl:Tt,originalEvent:e}),Dt({sortable:this,name:"sort",toEl:Tt,originalEvent:e})),bi.active&&(null!=Nt&&-1!==Nt||(Nt=zt,Vt=Lt),Dt({sortable:this,name:"end",toEl:Tt,originalEvent:e}),this.save())))),this._nulling()},_nulling:function(){St("nulling",this),It=At=Tt=Et=Pt=Mt=Rt=Ht=Ut=Ft=Wt=Nt=Vt=zt=Lt=Yt=Gt=qt=Ot=bi.dragged=bi.ghost=bi.clone=bi.active=null;var e=this.el;ai.forEach(function(t){e.contains(t)&&(t.checked=!0)}),ai.length=jt=Bt=0},handleEvent:function(e){switch(e.type){case"drop":case"dragend":this._onDrop(e);break;case"dragenter":case"dragover":At&&(this._onDragOver(e),function(e){e.dataTransfer&&(e.dataTransfer.dropEffect="move"),e.cancelable&&e.preventDefault()}(e));break;case"selectstart":e.preventDefault()}},toArray:function(){for(var e,t=[],i=this.el.children,s=0,r=i.length,o=this.options;s<r;s++)tt(e=i[s],o.draggable,this.el,!1)&&t.push(e.getAttribute(o.dataIdAttr)||$i(e));return t},sort:function(e,t){var i={},s=this.el;this.toArray().forEach(function(e,t){var r=s.children[t];tt(r,this.options.draggable,s,!1)&&(i[e]=r)},this),t&&this.captureAnimationState(),e.forEach(function(e){i[e]&&(s.removeChild(i[e]),s.appendChild(i[e]))}),t&&this.animateAll()},save:function(){var e=this.options.store;e&&e.set&&e.set(this)},closest:function(e,t){return tt(e,t||this.options.draggable,this.el,!1)},option:function(e,t){var i=this.options;if(void 0===t)return i[e];var s=kt.modifyOption(this,e,t);i[e]=void 0!==s?s:t,"group"===e&&gi(i)},destroy:function(){St("destroy",this);var e=this.el;e[xt]=null,Je(e,"mousedown",this._onTapStart),Je(e,"touchstart",this._onTapStart),Je(e,"pointerdown",this._onTapStart),this.nativeDraggable&&(Je(e,"dragover",this),Je(e,"dragenter",this)),Array.prototype.forEach.call(e.querySelectorAll("[draggable]"),function(e){e.removeAttribute("draggable")}),this._onDrop(),this._disableDelayedDragEvents(),ti.splice(ti.indexOf(this.el),1),this.el=e=null},_hideClone:function(){if(!Ht){if(St("hideClone",this),bi.eventCanceled)return;ot(Mt,"display","none"),this.options.removeCloneOnHide&&Mt.parentNode&&Mt.parentNode.removeChild(Mt),Ht=!0}},_showClone:function(e){if("clone"===e.lastPutMode){if(Ht){if(St("showClone",this),bi.eventCanceled)return;At.parentNode!=It||this.options.group.revertClone?Pt?It.insertBefore(Mt,Pt):It.appendChild(Mt):It.insertBefore(Mt,At),this.options.group.revertClone&&this.animate(At,Mt),ot(Mt,"display",""),Ht=!1}}else this._hideClone()}},ni&&Ke(document,"touchmove",function(e){(bi.active||Qt)&&e.cancelable&&e.preventDefault()}),bi.utils={on:Ke,off:Je,css:ot,find:nt,is:function(e,t){return!!tt(e,t,e,!1)},extend:function(e,t){if(e&&t)for(var i in t)t.hasOwnProperty(i)&&(e[i]=t[i]);return e},throttle:vt,closest:tt,toggleClass:rt,clone:ft,index:gt,nextTick:wi,cancelNextTick:ki,detectDirection:hi,getChild:pt,expando:xt},bi.get=function(e){return e[xt]},bi.mount=function(){for(var e=arguments.length,t=new Array(e),i=0;i<e;i++)t[i]=arguments[i];t[0].constructor===Array&&(t=t[0]),t.forEach(function(e){if(!e.prototype||!e.prototype.constructor)throw"Sortable: Mounted plugin must be a constructor function, not ".concat({}.toString.call(e));e.utils&&(bi.utils=qe(qe({},bi.utils),e.utils)),kt.mount(e)})},bi.create=function(e,t){return new bi(e,t)},bi.version="1.15.7";var Ci,Si,Di,Ai,Ti,Ei,Ii=[],Pi=!1;function Ri(){Ii.forEach(function(e){clearInterval(e.pid)}),Ii=[]}function Mi(){clearInterval(Ei)}var Hi=vt(function(e,t,i,s){if(t.scroll){var r,o=(e.touches?e.touches[0]:e).clientX,a=(e.touches?e.touches[0]:e).clientY,n=t.scrollSensitivity,l=t.scrollSpeed,d=lt(),c=!1;Si!==i&&(Si=i,Ri(),Ci=t.scroll,r=t.scrollFn,!0===Ci&&(Ci=ut(i,!0)));var p=0,h=Ci;do{var g=h,m=dt(g),u=m.top,_=m.bottom,v=m.left,b=m.right,f=m.width,y=m.height,x=void 0,$=void 0,w=g.scrollWidth,k=g.scrollHeight,C=ot(g),S=g.scrollLeft,D=g.scrollTop;g===d?(x=f<w&&("auto"===C.overflowX||"scroll"===C.overflowX||"visible"===C.overflowX),$=y<k&&("auto"===C.overflowY||"scroll"===C.overflowY||"visible"===C.overflowY)):(x=f<w&&("auto"===C.overflowX||"scroll"===C.overflowX),$=y<k&&("auto"===C.overflowY||"scroll"===C.overflowY));var A=x&&(Math.abs(b-o)<=n&&S+f<w)-(Math.abs(v-o)<=n&&!!S),T=$&&(Math.abs(_-a)<=n&&D+y<k)-(Math.abs(u-a)<=n&&!!D);if(!Ii[p])for(var E=0;E<=p;E++)Ii[E]||(Ii[E]={});Ii[p].vx==A&&Ii[p].vy==T&&Ii[p].el===g||(Ii[p].el=g,Ii[p].vx=A,Ii[p].vy=T,clearInterval(Ii[p].pid),0==A&&0==T||(c=!0,Ii[p].pid=setInterval(function(){s&&0===this.layer&&bi.active._onTouchMove(Ti);var t=Ii[this.layer].vy?Ii[this.layer].vy*l:0,i=Ii[this.layer].vx?Ii[this.layer].vx*l:0;"function"==typeof r&&"continue"!==r.call(bi.dragged.parentNode[xt],i,t,e,Ti,Ii[this.layer].el)||bt(Ii[this.layer].el,i,t)}.bind({layer:p}),24))),p++}while(t.bubbleScroll&&h!==d&&(h=ut(h,!1)));Pi=c}},30),zi=function(e){var t=e.originalEvent,i=e.putSortable,s=e.dragEl,r=e.activeSortable,o=e.dispatchSortableEvent,a=e.hideGhostForTarget,n=e.unhideGhostForTarget;if(t){var l=i||r;a();var d=t.changedTouches&&t.changedTouches.length?t.changedTouches[0]:t,c=document.elementFromPoint(d.clientX,d.clientY);n(),l&&!l.el.contains(c)&&(o("spill"),this.onSpill({dragEl:s,putSortable:i}))}};function Ni(){}function Li(){}Ni.prototype={startIndex:null,dragStart:function(e){var t=e.oldDraggableIndex;this.startIndex=t},onSpill:function(e){var t=e.dragEl,i=e.putSortable;this.sortable.captureAnimationState(),i&&i.captureAnimationState();var s=pt(this.sortable.el,this.startIndex,this.options);s?this.sortable.el.insertBefore(t,s):this.sortable.el.appendChild(t),this.sortable.animateAll(),i&&i.animateAll()},drop:zi},Ve(Ni,{pluginName:"revertOnSpill"}),Li.prototype={onSpill:function(e){var t=e.dragEl,i=e.putSortable||this.sortable;i.captureAnimationState(),t.parentNode&&t.parentNode.removeChild(t),i.animateAll()},drop:zi},Ve(Li,{pluginName:"removeOnSpill"}),bi.mount(new function(){function e(){for(var e in this.defaults={scroll:!0,forceAutoScrollFallback:!1,scrollSensitivity:30,scrollSpeed:10,bubbleScroll:!0},this)"_"===e.charAt(0)&&"function"==typeof this[e]&&(this[e]=this[e].bind(this))}return e.prototype={dragStarted:function(e){var t=e.originalEvent;this.sortable.nativeDraggable?Ke(document,"dragover",this._handleAutoScroll):this.options.supportPointer?Ke(document,"pointermove",this._handleFallbackAutoScroll):t.touches?Ke(document,"touchmove",this._handleFallbackAutoScroll):Ke(document,"mousemove",this._handleFallbackAutoScroll)},dragOverCompleted:function(e){var t=e.originalEvent;this.options.dragOverBubble||t.rootEl||this._handleAutoScroll(t)},drop:function(){this.sortable.nativeDraggable?Je(document,"dragover",this._handleAutoScroll):(Je(document,"pointermove",this._handleFallbackAutoScroll),Je(document,"touchmove",this._handleFallbackAutoScroll),Je(document,"mousemove",this._handleFallbackAutoScroll)),Mi(),Ri(),clearTimeout(it),it=void 0},nulling:function(){Ti=Si=Ci=Pi=Ei=Di=Ai=null,Ii.length=0},_handleFallbackAutoScroll:function(e){this._handleAutoScroll(e,!0)},_handleAutoScroll:function(e,t){var i=this,s=(e.touches?e.touches[0]:e).clientX,r=(e.touches?e.touches[0]:e).clientY,o=document.elementFromPoint(s,r);if(Ti=e,t||this.options.forceAutoScrollFallback||Be||je||Ze){Hi(e,this.options,o,t);var a=ut(o,!0);!Pi||Ei&&s===Di&&r===Ai||(Ei&&Mi(),Ei=setInterval(function(){var o=ut(document.elementFromPoint(s,r),!0);o!==a&&(a=o,Ri()),Hi(e,i.options,o,t)},10),Di=s,Ai=r)}else{if(!this.options.bubbleScroll||ut(o,!0)===lt())return void Ri();Hi(e,this.options,ut(o,!1),!1)}}},Ve(e,{pluginName:"scroll",initializeByDefault:!0})}),bi.mount(Li,Ni);const Vi=a`
    .action-btn {
        background: none;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        padding: 4px 10px;
        font-size: 0.75rem;
        font-weight: 500;
        font-family: inherit;
        color: var(--primary-color);
        cursor: pointer;
        text-transform: uppercase;
        letter-spacing: 0.03em;
        transition: background 150ms ease, color 150ms ease,
                    border-color 150ms ease, box-shadow 300ms ease;
    }
    .action-btn:hover {
        background: var(--secondary-background-color);
    }
    .action-btn:disabled {
        opacity: 0.5;
        cursor: default;
    }

    /* Semantic chip colors -- the one palette, everywhere. */
    .action-btn.assign-btn {
        color: #2e7d32;
        border-color: rgba(46, 125, 50, 0.3);
        position: relative; /* anchor for the green assignment dot */
    }
    .action-btn.assign-btn:hover {
        background: rgba(46, 125, 50, 0.08);
    }
    .action-btn.test-btn {
        color: var(--primary-color);
    }
    .action-btn.trigger-btn {
        color: #b89930;
        border-color: rgba(184, 153, 48, 0.3);
        position: relative; /* anchor for the yellow trigger dot */
    }
    .action-btn.trigger-btn:hover {
        background: rgba(184, 153, 48, 0.08);
    }
    .action-btn.delete-btn {
        color: #e65100;
        border-color: rgba(230, 81, 0, 0.25);
    }
    .action-btn.delete-btn:hover {
        background: rgba(230, 81, 0, 0.08);
    }
    .action-btn.dismiss-btn {
        color: var(--secondary-text-color);
        border-color: var(--divider-color);
        position: relative; /* anchor for the dot indicator */
    }
`;let Oi=class extends ne{constructor(){super(...arguments),this.color="green",this.count=0}render(){if(this.count<1)return F``;const e=this.count>=10;return F`<span
            class="dot badge ${this.color} ${e?"multi-digit":""}"
            ><span class="digit">${this.count}</span></span
        >`}};Oi.styles=a`
        /* The host generates no box; each dot is absolutely positioned against
           the calling button (which sets position: relative). This keeps the
           dot out of inline flow, so a numbered badge cannot pick up a
           line-box strut and drift downward the way an inline-flex child does. */
        :host {
            display: contents;
        }
        .dot {
            position: absolute;
            pointer-events: none;
            box-shadow: 0 0 0 1.5px var(--card-background-color);
        }
        /* Numbered 10px badge for count 1..9. Anchored at -5 so the box
           centres on the button's top-right corner point. (A bare unnumbered
           dot for count 1 existed through v0.6.1; retired on the v0.6.6
           bench -- every count shows its number now.) */
        .dot.badge {
            top: -5px;
            right: -5px;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            color: #ffffff;
            /* 8px (not 7px) rasterises crisply at this size and reads as
               centred; 7px snapped to the pixel grid and looked off. */
            font-size: 8px;
            font-weight: 500;
            line-height: 1;
            /* The action buttons set letter-spacing, which inherits here and
               adds phantom space to the RIGHT of the single digit -- the flex
               box then centres [digit + that space], shoving the digit left.
               Reset it so the digit centres on its own advance. */
            letter-spacing: normal;
            /* Every numeral on the same uniform advance width, so 1, 2,
               and 9 all land at the identical spot in the circle. Without
               this, each digit centres on its own advance and the dots
               visibly disagree with each other (owner bench, shampoo). */
            font-variant-numeric: tabular-nums;
        }
        /* Optical centring for the digit's shared bias: half a pixel right
           and half down from true flex centre (subpixel transforms render
           antialiased -- dialled on the bench across three passes). With
           tabular-nums above, this one value holds for every digit. */
        .dot.badge .digit {
            display: block;
            transform: translate(0.5px, 0.5px);
        }
        /* Double-digit stretch for count >= 10 (wider pill, pulled out a touch
           further so it clears the corner). */
        .dot.badge.multi-digit {
            right: -6px;
            min-width: 10px;
            padding: 0 3px;
            border-radius: 5px;
        }
        /* Colour variants */
        .dot.green {
            background: #2e7d32;
        }
        .dot.yellow {
            background: #b89930;
        }
    `,e([pe({type:String})],Oi.prototype,"color",void 0),e([pe({type:Number})],Oi.prototype,"count",void 0),Oi=e([me("ir-count-dot")],Oi);let qi=class extends ne{constructor(){super(...arguments),this.templateName="",this.command=null,this.busy=!1,this.actionLabel=null,this.hasTrigger=!1,this.triggerCount=0,this.showActionMapping=!0,this._editingName=!1,this._draftName=""}_commandLabel(){const e=this.command;return e.protocol&&e.code?`${e.protocol}: ${e.code}`:e.raw_timings?.length?$e("cmdrow.raw_timings",{count:e.raw_timings.length}):e.protocol??"IR"}_prontoSlArray(e){const t=e.trim().split(/\s+/);if(t.length<6)return null;const i=parseInt(t[2],16)+parseInt(t[3],16),s=t.slice(4);if(s.length<2*i)return null;const r=[];for(let e=0;e<2*i;e++){const t=parseInt(s[e],16);r.push(t>=48)}return r.length>0?r:null}_renderDiamonds(){const e=this.command;if(!e||"PRONTO"!==e.protocol?.toUpperCase()||!e.code)return null;const t=this._prontoSlArray(e.code);return t?F`<span class="diamonds">${t.map(e=>e?F`<span class="diamond long">◆</span>`:F`<span class="diamond short">◇</span>`)}</span>`:null}_emit(e,t){const i=t?.currentTarget?.getBoundingClientRect()??null;this.dispatchEvent(new CustomEvent(e,{detail:{templateName:this.templateName,command:this.command,buttonRect:i},bubbles:!0,composed:!0}))}_startRename(e){this.command&&!this.busy&&(e.stopPropagation(),this._draftName=this.command.name,this._editingName=!0,this.updateComplete.then(()=>{const e=this.shadowRoot?.querySelector(".name-input");e?.focus(),e?.select()}))}_commitRename(){if(!this._editingName)return;const e=this._draftName.trim();this._editingName=!1,this.command&&e&&e!==this.command.name&&this.dispatchEvent(new CustomEvent("rename-command",{detail:{command:this.command,name:e},bubbles:!0,composed:!0}))}_onRenameKeydown(e){"Enter"===e.key?(e.preventDefault(),this._commitRename()):"Escape"===e.key&&(this._editingName=!1)}render(){const e=null!==this.command,t=e?this._renderDiamonds():null;return F`
            <div class="row" data-learned=${e?"true":"false"}>
                <div class="status" aria-hidden="true">
                    <slot name="status"></slot>
                </div>
                <div class="info">
                    <div class="name">
                        ${e?this._editingName?F`<input
                                      class="name-input"
                                      type="text"
                                      .value=${this._draftName}
                                      @input=${e=>this._draftName=e.target.value}
                                      @keydown=${this._onRenameKeydown}
                                      @blur=${this._commitRename}
                                  />`:F`<span
                                      class="editable-name"
                                      title=${$e("cmdrow.rename")}
                                      @click=${this._startRename}
                                      >${this.templateName}<span class="rename-pencil"
                                          >&#9998;</span
                                      ></span
                                  >`:F`${this.templateName}`}
                        ${e&&this.command?.decoded_fingerprint?F`<button
                                  class="tx-pill ${this.command.tx_force_raw?"tx-raw-on":""}"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("toggle-tx-raw")}
                                  title=${this.command.tx_force_raw?$e("cmdrow.tx_raw_on"):$e("cmdrow.tx_raw_off")}
                              >${this.command.tx_force_raw?"PRONTO":this.command.decoded_protocol??"AUTO"}</button>`:""}
                        ${e&&this.command&&this.command.send_count>1?F`<span
                                  class="repeat-indicator"
                                  title=${$e("cmdrow.sends_times",{count:this.command.send_count})}
                                  ><ha-svg-icon
                                      .path=${"M17,17H7V14L3,18L7,22V19H19V13H17M7,7H17V10L21,6L17,2V5H5V11H7V7Z"}
                                  ></ha-svg-icon
                                  >${this.command.send_count}</span
                              >`:""}
                        ${e&&this.command&&this.command.repeat_count>1&&this.command.decoded_protocol&&!this.command.tx_force_raw?F`<span
                                  class="ditto-indicator"
                                  title=${$e("cmdrow.dittos",{count:this.command.repeat_count})}
                                  ><ha-svg-icon
                                      .path=${"M16,12A2,2 0 0,1 18,10A2,2 0 0,1 20,12A2,2 0 0,1 18,14A2,2 0 0,1 16,12M10,12A2,2 0 0,1 12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12M4,12A2,2 0 0,1 6,10A2,2 0 0,1 8,12A2,2 0 0,1 6,14A2,2 0 0,1 4,12Z"}
                                  ></ha-svg-icon
                                  >${this.command.repeat_count}</span
                              >`:""}
                    </div>
                    <div class="meta">
                        ${t||(e?F`${this._commandLabel()}`:F`<span class="muted">${$e("cmdrow.not_learned")}</span>`)}
                    </div>
                </div>
                <div class="actions">
                    ${e?F`
                              <button
                                  class="icon-btn edit-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("edit-command")}
                                  title=${$e("cmdrow.edit_code")}
                              ><ha-svg-icon
                                      class="edit-glyph"
                                      .path=${"M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"}
                                  ></ha-svg-icon></button>
                              ${this.showActionMapping?F`<button
                                  class="action-btn badge-btn"
                                  ?data-mapped=${!!this.actionLabel}
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("map-action")}
                                  title=${$e("cmdrow.map_action")}
                              >${this.actionLabel||$e("cmdrow.actions")}</button>`:""}
                              <button
                                  class="action-btn test-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("test")}
                              >${$e("cmdrow.test")}</button>
                              <button
                                  class="action-btn trigger-btn"
                                  ?disabled=${this.busy}
                                  @click=${e=>this._emit("toggle-trigger",e)}
                                  title=${this.hasTrigger?$e("cmdrow.edit_trigger"):$e("cmdrow.create_trigger")}
                              >${$e("cmdrow.trigger")}<ir-count-dot
                                      color="yellow"
                                      .count=${this.triggerCount||(this.hasTrigger?1:0)}
                                  ></ir-count-dot></button>
                              <button
                                  class="action-btn delete-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("delete")}
                              >${$e("cmdrow.delete")}</button>
                          `:F`
                              <button
                                  class="action-btn learn-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("learn")}
                              >${$e("cmdrow.learn")}</button>
                          `}
                </div>
            </div>
        `}};qi.styles=a`
        :host {
            display: block;
        }
        :host(:not(:last-of-type)) {
            margin-bottom: 4px;
        }
        .row {
            display: grid;
            grid-template-columns: 32px 1fr auto;
            align-items: center;
            gap: 12px;
            padding: 8px 10px;
            /* Match the page background so the long horizontal command
               strips visually merge with the device-detail backdrop
               instead of reading as highlighted bands. Themes that
               distinguish primary vs secondary background colors will
               carry both through naturally; themes that keep them
               equal end up with the same visual effect. The hover
               state on action buttons inside the row still uses
               --secondary-background-color so the button hover remains
               distinguishable. */
            background: var(--primary-background-color);
            border-radius: 4px;
        }
        .status {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .name {
            display: flex;
            align-items: center;
            gap: 7px;
            flex-wrap: wrap;
            font-weight: 500;
        }
        .editable-name {
            cursor: pointer;
            position: relative;
            display: inline-flex;
            align-items: center;
            border-bottom: 1px dashed transparent;
            transition: border-color 150ms ease;
        }
        .editable-name:hover {
            border-bottom-color: var(--primary-color);
        }
        .rename-pencil {
            /* Out of layout flow so it reserves no width: the name-to-pill
               gap stays the true 7px flex gap (matches pill-to-count).
               Tucked over the tail of the name; fades in on hover and never
               reaches the pill. */
            position: absolute;
            left: 100%;
            top: 50%;
            transform: translate(-50%, -50%);
            pointer-events: none;
            font-size: 0.7rem;
            color: var(--secondary-text-color);
            opacity: 0;
            transition: opacity 150ms ease;
        }
        .editable-name:hover .rename-pencil {
            opacity: 1;
        }
        .name-input {
            font-size: inherit;
            font-weight: 500;
            font-family: inherit;
            border: none;
            border-bottom: 2px solid var(--primary-color);
            background: transparent;
            color: var(--primary-text-color);
            outline: none;
            padding: 0 0 1px;
            min-width: 120px;
        }
        .repeat-indicator {
            display: inline-flex;
            align-items: center;
            gap: 1px;
            font-size: 9px;
            font-weight: 600;
            /* Match the short-diamond orange; bare (no pill) on the name line.
               Vertically centered in line with the pill via the name flex.
               Slight knock-down to sit softer next to the pill. */
            color: var(--warning-color, #ff9800);
            opacity: 0.85;
        }
        .repeat-indicator ha-svg-icon {
            --mdc-icon-size: 10px;
        }
        .ditto-indicator {
            display: inline-flex;
            align-items: center;
            gap: 1px;
            font-size: 9px;
            font-weight: 600;
            /* Match the long-diamond blue (decoded protocol); same size as the
               orange send-count indicator it sits beside. */
            color: var(--primary-color);
            opacity: 0.85;
        }
        .ditto-indicator ha-svg-icon {
            --mdc-icon-size: 10px;
        }
        .icon-btn {
            background: none;
            border: none;
            padding: 2px;
            display: inline-flex;
            align-items: center;
            cursor: pointer;
            color: var(--secondary-text-color);
        }
        .icon-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .icon-btn:hover:not(:disabled) {
            color: var(--primary-text-color);
        }
        .edit-glyph {
            --mdc-icon-size: 10px;
        }
        .meta {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            font-family: var(--code-font-family, monospace);
        }
        .muted {
            font-style: italic;
        }
        .diamonds {
            display: inline-flex;
            gap: 1px;
            flex-wrap: wrap;
            line-height: 1;
        }
        .diamond {
            font-size: 0.7rem;
        }
        .diamond.long {
            color: var(--primary-color);
        }
        .diamond.short {
            color: var(--warning-color, #ff9800);
        }
        .actions {
            display: flex;
            gap: 4px;
            align-items: center;
        }
        .action-btn {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 0.75rem;
            font-weight: 500;
            font-family: inherit;
            color: var(--primary-color);
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            transition: background 150ms ease;
        }
        .action-btn:hover {
            background: var(--secondary-background-color);
        }
        .action-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .action-btn.test-btn {
            color: #2e7d32;
            border-color: rgba(46, 125, 50, 0.3);
        }
        .action-btn.test-btn:hover {
            background: rgba(46, 125, 50, 0.08);
        }
        .action-btn.learn-btn {
            color: #fff;
            background: #2e7d32;
            border-color: #2e7d32;
        }
        .action-btn.learn-btn:hover {
            background: #1b5e20;
        }
        .action-btn.badge-btn {
            color: var(--secondary-text-color, #999);
            border-color: var(--divider-color);
            min-width: 50px;
            text-align: center;
        }
        .action-btn.badge-btn[data-mapped] {
            color: var(--primary-color);
            border-color: var(--primary-color);
            background: rgba(var(--rgb-primary-color, 33, 150, 243), 0.08);
        }
        .action-btn.badge-btn:hover {
            background: rgba(var(--rgb-primary-color, 33, 150, 243), 0.12);
        }
        .action-btn.trigger-btn {
            position: relative;
            color: #b89930;
            border-color: rgba(184, 153, 48, 0.3);
        }
        .action-btn.trigger-btn:hover {
            background: rgba(184, 153, 48, 0.08);
        }
        .action-btn.delete-btn {
            color: #e65100;
            border-color: rgba(230, 81, 0, 0.25);
        }
        .action-btn.delete-btn:hover {
            background: rgba(230, 81, 0, 0.08);
        }
        /* Protocol toggle on the name line: a tiny solid pill with white
           text. Blue fill = decoded protocol (NEC); orange fill = the
           captured-replay (PRONTO) override. Same tx_force_raw toggle. */
        .tx-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            box-sizing: border-box;
            height: 11px;
            border: none;
            border-radius: 999px;
            /* Slightly more top than bottom pad to optically center the caps. */
            padding: 1px 5px 0;
            font-size: 9px;
            font-weight: 500;
            font-family: inherit;
            letter-spacing: 0.03em;
            line-height: 1;
            color: #fff;
            /* Soften the fill (not the whole pill) so the white text stays
               crisp while the hue reads lighter / less poppy than the diamonds. */
            background: color-mix(in srgb, var(--primary-color) 82%, transparent);
            cursor: pointer;
            transition: opacity 150ms ease;
        }
        .tx-pill.tx-raw-on {
            /* Match the short-diamond orange, softened the same amount. */
            background: color-mix(in srgb, var(--warning-color, #ff9800) 82%, transparent);
        }
        .tx-pill:hover:not(:disabled) {
            opacity: 0.85;
        }
        .tx-pill:disabled {
            opacity: 0.5;
            cursor: default;
        }
    `,e([pe({attribute:!1})],qi.prototype,"templateName",void 0),e([pe({attribute:!1})],qi.prototype,"command",void 0),e([pe({type:Boolean})],qi.prototype,"busy",void 0),e([pe({attribute:!1})],qi.prototype,"actionLabel",void 0),e([pe({type:Boolean})],qi.prototype,"hasTrigger",void 0),e([pe({type:Number})],qi.prototype,"triggerCount",void 0),e([pe({type:Boolean})],qi.prototype,"showActionMapping",void 0),e([he()],qi.prototype,"_editingName",void 0),e([he()],qi.prototype,"_draftName",void 0),qi=e([me("ir-command-row")],qi);let Ui=class extends ne{constructor(){super(...arguments),this.commandName="",this.timeout=15,this._phase="listening",this._result=null,this._duplicate=null,this._error=null,this._timeRemaining=0,this._sessionId=null,this._unsubscribe=null,this._countdown=null}connectedCallback(){super.connectedCallback(),this._beginCapture()}disconnectedCallback(){super.disconnectedCallback(),this._stopCountdown(),this._unsubscribe&&(this._unsubscribe(),this._unsubscribe=null)}async _beginCapture(){this._phase="listening",this._result=null,this._duplicate=null,this._error=null,this._timeRemaining=this.timeout,this._startCountdown();try{const{session:e,unsubscribe:t}=await this.api.startCapture(this.device.id,this.timeout,e=>this._onCaptureEvent(e));this._sessionId=e.session_id,this._unsubscribe=t}catch(e){this._stopCountdown(),this._error=e.message,this._phase="error"}}_onCaptureEvent(e){switch(e.type){case"capture_listening":this._phase="listening";break;case"capture_received":this._stopCountdown(),this._result=e.result,e.duplicate_of?(this._duplicate=e.duplicate_of,this._phase="duplicate"):this._phase="captured";break;case"capture_timeout":this._stopCountdown(),this._phase="timeout";break;case"capture_error":this._stopCountdown(),this._error=e.error,this._phase="error";break;case"capture_cancelled":this._stopCountdown(),this._close()}}_startCountdown(){this._stopCountdown();const e=Date.now();this._countdown=window.setInterval(()=>{const t=(Date.now()-e)/1e3;this._timeRemaining=Math.max(0,Math.ceil(this.timeout-t)),this._timeRemaining<=0&&this._stopCountdown()},250)}_stopCountdown(){null!==this._countdown&&(clearInterval(this._countdown),this._countdown=null)}async _cancel(){if(this._sessionId)try{await this.api.cancelCapture(this._sessionId)}catch{}this._close()}async _testCommand(){if(!this._sessionId)return;const e=`__hair_test_${Date.now()}`;try{const t=await this.api.saveCapturedCommand({device_id:this.device.id,session_id:this._sessionId,command_name:e});await this.api.sendCommand(this.device.id,t.id),await this.api.deleteCommand(this.device.id,t.id)}catch(e){this._error=e.message,this._phase="error"}}async _save(e){if(this._sessionId)try{await this.api.saveCapturedCommand({device_id:this.device.id,session_id:this._sessionId,command_name:this.commandName}),this.dispatchEvent(new CustomEvent("command-saved",{detail:{saveAndNext:e,commandName:this.commandName},bubbles:!0,composed:!0})),this._close()}catch(e){this._error=e.message,this._phase="error"}}async _recapture(){this._unsubscribe&&(await this._unsubscribe(),this._unsubscribe=null),await this._beginCapture()}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_renderListening(){return F`
            <div class="phase listening" aria-live="polite">
                <div class="pulse" aria-hidden="true">
                    <span></span><span></span><span></span>
                </div>
                <div class="title">${$e("capture.listening")}</div>
                <div class="instruction">
                    ${$e("capture.instruction",{name:this.commandName})}
                </div>
                <div class="countdown">
                    ${$e("capture.remaining",{seconds:this._timeRemaining})}
                </div>
                <div class="actions">
                    <mwc-button @click=${this._cancel}>${$e("common.cancel")}</mwc-button>
                </div>
            </div>
        `}_renderCaptured(){const e=this._result;return F`
            <div class="phase captured" aria-live="polite">
                <div class="check" aria-hidden="true">✓</div>
                <div class="title">${$e("capture.captured")}</div>
                <div class="meta">
                    ${$e("capture.protocol",{protocol:e.protocol??$e("capture.protocol_raw")})}${e.code?F` · <code>${e.code}</code>`:""}
                </div>
                <ha-alert alert-type="info">
                    ${$e("capture.verify")}
                </ha-alert>
                <div class="actions">
                    <mwc-button @click=${this._testCommand}>${$e("capture.test")}</mwc-button>
                    <mwc-button @click=${this._recapture}>${$e("capture.recapture")}</mwc-button>
                    <mwc-button raised @click=${()=>this._save(!0)}>
                        ${$e("capture.save_next")}
                    </mwc-button>
                </div>
            </div>
        `}_renderTimeout(){return F`
            <div class="phase error" aria-live="assertive">
                <div class="title warn">${$e("capture.no_signal")}</div>
                <ul class="tips">
                    <li>${$e("capture.tip_point")}</li>
                    <li>${$e("capture.tip_closer")}</li>
                    <li>${$e("capture.tip_hold")}</li>
                </ul>
                <div class="actions">
                    <mwc-button raised @click=${this._recapture}>${$e("capture.try_again")}</mwc-button>
                    <mwc-button @click=${this._cancel}>${$e("common.cancel")}</mwc-button>
                </div>
            </div>
        `}_renderDuplicate(){const e=this._result;return F`
            <div class="phase warning" aria-live="assertive">
                <div class="title warn">${$e("capture.duplicate")}</div>
                <div class="instruction">
                    ${$e("capture.duplicate_instruction",{name:this._duplicate.name})}
                </div>
                <div class="meta">
                    ${$e("capture.protocol",{protocol:e.protocol??$e("capture.protocol_raw")})}
                </div>
                <div class="actions">
                    <mwc-button @click=${this._recapture}>
                        ${$e("capture.recapture_different")}
                    </mwc-button>
                    <mwc-button raised @click=${()=>this._save(!0)}>
                        ${$e("capture.save_anyway")}
                    </mwc-button>
                </div>
            </div>
        `}_renderError(){return F`
            <div class="phase error" aria-live="assertive">
                <div class="title warn">${$e("capture.error")}</div>
                <div class="instruction">${this._error}</div>
                <div class="actions">
                    <mwc-button raised @click=${this._recapture}>
                        ${$e("capture.try_again")}
                    </mwc-button>
                    <mwc-button @click=${this._cancel}>${$e("common.cancel")}</mwc-button>
                </div>
            </div>
        `}render(){return F`
            <ha-dialog
                open
                heading=${$e("capture.learning",{name:this.commandName})}
                @closed=${this._cancel}
            >
                ${"listening"===this._phase?this._renderListening():"captured"===this._phase?this._renderCaptured():"timeout"===this._phase?this._renderTimeout():"duplicate"===this._phase?this._renderDuplicate():this._renderError()}
            </ha-dialog>
        `}};Ui.styles=a`
        .phase {
            min-width: 320px;
            padding: 8px 0;
        }
        .title {
            font-size: 1.1rem;
            font-weight: 500;
            margin-bottom: 8px;
        }
        .title.warn {
            color: var(--warning-color, #ffa600);
        }
        .instruction {
            color: var(--primary-text-color);
            margin-bottom: 8px;
        }
        .meta {
            color: var(--secondary-text-color);
            font-size: 0.85rem;
            margin-bottom: 8px;
        }
        .countdown {
            margin: 10px 0;
            font-variant-numeric: tabular-nums;
            color: var(--secondary-text-color);
        }
        .check {
            font-size: 3rem;
            color: var(--success-color, #43a047);
            text-align: center;
            margin: 8px 0;
        }
        .pulse {
            display: flex;
            justify-content: center;
            gap: 6px;
            margin: 8px 0 16px;
        }
        .pulse span {
            display: inline-block;
            width: 12px;
            height: 12px;
            background: var(--primary-color);
            border-radius: 50%;
            opacity: 0.4;
            animation: pulse 1s infinite ease-in-out;
        }
        .pulse span:nth-child(2) {
            animation-delay: 0.2s;
        }
        .pulse span:nth-child(3) {
            animation-delay: 0.4s;
        }
        @keyframes pulse {
            0%,
            100% {
                opacity: 0.3;
                transform: scale(0.85);
            }
            50% {
                opacity: 1;
                transform: scale(1.1);
            }
        }
        .actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            margin-top: 16px;
            flex-wrap: wrap;
        }
        .tips {
            margin: 4px 0 12px;
            padding-left: 22px;
            color: var(--primary-text-color);
        }
    `,e([pe({attribute:!1})],Ui.prototype,"api",void 0),e([pe({attribute:!1})],Ui.prototype,"hass",void 0),e([pe({attribute:!1})],Ui.prototype,"device",void 0),e([pe({attribute:!1})],Ui.prototype,"commandName",void 0),e([pe({attribute:!1})],Ui.prototype,"timeout",void 0),e([he()],Ui.prototype,"_phase",void 0),e([he()],Ui.prototype,"_result",void 0),e([he()],Ui.prototype,"_duplicate",void 0),e([he()],Ui.prototype,"_error",void 0),e([he()],Ui.prototype,"_timeRemaining",void 0),e([he()],Ui.prototype,"_sessionId",void 0),Ui=e([me("ir-capture-dialog")],Ui);const Fi=a`
    /* --- Custom overlay shell (dialogs not hosted in <ha-dialog>) --- */
    .overlay {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 100;
    }
    .dialog {
        background: var(--card-background-color, #fff);
        border-radius: 12px;
        padding: 24px;
        max-width: 400px;
        width: 90%;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    .heading {
        margin: 0 0 16px;
        font-size: 1.1rem;
        font-weight: 500;
        color: var(--primary-text-color);
    }

    /* --- Form fields --- */
    .field {
        display: block;
        margin: 12px 0;
        width: 100%;
    }
    .field label {
        display: block;
        font-size: 0.85rem;
        color: var(--secondary-text-color);
        margin-bottom: 6px;
    }
    input[type="text"],
    select {
        width: 100%;
        padding: 8px;
        border-radius: 4px;
        border: 1px solid var(--divider-color);
        background: var(--card-background-color);
        color: var(--primary-text-color);
        font-size: 0.95rem;
        font-family: inherit;
        box-sizing: border-box;
    }
    input[type="text"]:focus,
    select:focus {
        outline: none;
        border-color: var(--primary-color);
    }

    /* --- Actions row --- */
    .dialog-actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        margin-top: 20px;
        padding-top: 16px;
        border-top: 1px solid var(--divider-color);
    }

    /* --- Action buttons: outlined family (the majority) --- */
    .action-btn {
        background: none;
        border: 1px solid var(--divider-color);
        border-radius: 4px;
        padding: 8px 16px;
        font-size: 0.85rem;
        font-weight: 500;
        font-family: inherit;
        cursor: pointer;
        transition: background 150ms ease;
    }
    .action-btn:disabled {
        opacity: 0.5;
        cursor: default;
    }

    /* --- Action buttons: solid borderless family (assign/promote) --- */
    .action-btn.wide {
        padding: 8px 20px;
        font-size: 0.9rem;
        border: none;
        transition: background 150ms ease, opacity 150ms ease;
    }
    .action-btn.wide:disabled {
        cursor: not-allowed;
    }

    /* --- The cancel button, identical everywhere --- */
    .cancel-btn {
        background: transparent;
        color: var(--secondary-text-color);
    }
    .cancel-btn:hover:not(:disabled) {
        background: var(--secondary-background-color);
    }
`;let ji=class extends ne{constructor(){super(...arguments),this.title="",this.message="",this.confirmLabel="",this.cancelLabel="",this.destructive=!1,this._busy=!1}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_confirm(){this.dispatchEvent(new CustomEvent("confirmed",{bubbles:!0,composed:!0}))}render(){return F`
            <div class="overlay" @click=${this._close}>
                <div class="dialog" @click=${e=>e.stopPropagation()}>
                    <h3 class="heading">${this.title||$e("common.confirm")}</h3>
                    <p class="message">${this.message||$e("common.are_you_sure")}</p>
                    <div class="actions">
                        <button class="btn cancel" @click=${this._close}>
                            ${this.cancelLabel||$e("common.cancel")}
                        </button>
                        <button
                            class="btn confirm ${this.destructive?"destructive":""}"
                            @click=${this._confirm}
                        >
                            ${this.confirmLabel||$e("common.confirm")}
                        </button>
                    </div>
                </div>
            </div>
        `}};ji.styles=[Fi,a`
        /* Tighter heading than the shared 16px; ships this way. */
        .heading {
            margin: 0 0 12px;
        }
        .message {
            margin: 0 0 20px;
            color: var(--secondary-text-color);
            line-height: 1.5;
            font-size: 0.95rem;
        }
        .actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
        }
        .btn {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 6px;
            padding: 8px 20px;
            font-size: 0.85rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            transition: background 150ms ease;
        }
        .btn:hover {
            background: var(--secondary-background-color);
        }
        .cancel {
            color: var(--secondary-text-color);
        }
        .confirm {
            color: #fff;
            background: var(--primary-color);
            border-color: var(--primary-color);
        }
        .confirm:hover {
            opacity: 0.9;
        }
        .confirm.destructive {
            background: #e65100;
            border-color: #e65100;
        }
    `],e([pe()],ji.prototype,"title",void 0),e([pe()],ji.prototype,"message",void 0),e([pe()],ji.prototype,"confirmLabel",void 0),e([pe()],ji.prototype,"cancelLabel",void 0),e([pe({type:Boolean})],ji.prototype,"destructive",void 0),e([he()],ji.prototype,"_busy",void 0),ji=e([me("ir-confirm-dialog")],ji);let Bi=class extends ne{constructor(){super(...arguments),this.value=[],this.disabled=!1,this.excludeEntityIds=[],this._didAutoSelect=!1,this._receiverIds=new Set,this._receiversLoaded=!1}updated(e){if(super.updated(e),e.has("api")&&this.api&&!this._receiversLoaded&&(this._receiversLoaded=!0,this._loadReceivers()),!this._didAutoSelect)if(this.value.length>0)this._didAutoSelect=!0;else{const e=this._getEmitters();1===e.length&&(this._didAutoSelect=!0,this._fireChange([e[0].entity_id]))}}async _loadReceivers(){if(this.api)try{const e=await this.api.listReceivers();this._receiverIds=new Set(e.map(e=>e.entity_id))}catch{this._receiverIds=new Set}}_getEmitters(){const e=this.hass?.states??{},t=new Set(this.excludeEntityIds),i=[];for(const[s,r]of Object.entries(e))!s.startsWith("infrared.")||t.has(s)||this._receiverIds.has(s)||r.attributes.hair_observer||i.push({entity_id:s,name:r.attributes.friendly_name??s});return i}_emitterName(e){const t=this.hass?.states?.[e];return t?.attributes?.friendly_name??e}_onAdd(e){const t=e.target,i=t.value;i&&(t.value="",this.value.includes(i)||this._fireChange([...this.value,i]))}_onRemove(e){this._fireChange(this.value.filter(t=>t!==e))}_fireChange(e){this.value=e,this.dispatchEvent(new CustomEvent("emitters-changed",{detail:{value:e},bubbles:!0,composed:!0}))}render(){const e=this._getEmitters(),t=e.filter(e=>!this.value.includes(e.entity_id));return F`
            <label>${$e("picker.emitters_label")}</label>

            ${this.value.length>0?F`
                      <div class="chips">
                          ${this.value.map(e=>F`
                                  <span class="chip">
                                      <span class="chip-name">${this._emitterName(e)}</span>
                                      ${this.disabled?"":F`<button
                                                class="chip-remove"
                                                @click=${()=>this._onRemove(e)}
                                                title=${$e("common.remove")}
                                            >&times;</button>`}
                                  </span>
                              `)}
                      </div>
                  `:""}

            ${0===e.length?F`<div class="no-emitters">${$e("picker.no_emitters")}</div>`:t.length>0?F`
                        <select
                            @change=${this._onAdd}
                            ?disabled=${this.disabled}
                        >
                            <option value="">${$e("picker.add_emitter")}</option>
                            ${t.map(e=>F`
                                    <option value=${e.entity_id}>
                                        ${e.name}
                                    </option>
                                `)}
                        </select>
                    `:this.value.length>0?F`<div class="all-selected">${$e("picker.all_emitters_selected")}</div>`:""}
        `}};Bi.styles=a`
        :host {
            display: block;
        }
        label {
            display: var(--picker-label-display, block);
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--secondary-text-color);
            margin-bottom: 6px;
        }
        .chips {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 8px;
        }
        .chip {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: var(--secondary-background-color);
            color: #ff9800;
            font-size: 0.82rem;
            font-weight: 500;
            padding: 4px 8px;
            border-radius: 4px;
            line-height: 1;
        }
        .chip-name {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 200px;
        }
        .chip-remove {
            background: none;
            border: none;
            color: inherit;
            font-size: 1rem;
            cursor: pointer;
            padding: 0 2px;
            line-height: 1;
            opacity: 0.65;
            transition: opacity 120ms ease;
        }
        .chip-remove:hover {
            opacity: 1;
        }
        select {
            width: 100%;
            padding: 6px 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-family: inherit;
            font-size: 0.85rem;
        }
        .no-emitters {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
        .all-selected {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
    `,e([pe({attribute:!1})],Bi.prototype,"hass",void 0),e([pe({attribute:!1})],Bi.prototype,"api",void 0),e([pe({attribute:!1})],Bi.prototype,"value",void 0),e([pe({type:Boolean})],Bi.prototype,"disabled",void 0),e([pe({attribute:!1})],Bi.prototype,"excludeEntityIds",void 0),e([he()],Bi.prototype,"_didAutoSelect",void 0),e([he()],Bi.prototype,"_receiverIds",void 0),Bi=e([me("ir-emitter-picker")],Bi);const Xi=[3e4,33e3,36e3,38e3,4e4,56e3],Zi=e=>Xi.reduce((t,i)=>Math.abs(i-e)<Math.abs(t-e)?i:t);let Wi=class extends ne{constructor(){super(...arguments),this.signalId=null,this.commandId=null,this.initialPronto="",this.initialAlias="",this.initialSendCount=1,this.initialDitto=1,this.initialObservedRepeatCount=0,this.initialTxForceRaw=!1,this.initialDecodedProtocol=null,this.hasTrigger=!1,this.allowSnap=!1,this._pronto="",this._alias="",this._sendCount=1,this._ditto=1,this._busy=!1,this._error=null,this._validation=null,this._copyHint=null,this._snapping=!1,this._snapFlash=!1,this._debounce=null}get _isCommand(){return null!==this.commandId}get _isEdit(){return null!==this.signalId||null!==this.commandId}get _dirty(){return this._pronto!==this.initialPronto||this._alias!==this.initialAlias||this._sendCount!==this.initialSendCount||this._ditto!==this.initialDitto}get _canSave(){return!this._busy&&!0===this._validation?.valid&&(!this._isEdit||this._dirty)}get _dittoCountDisabled(){return this._isCommand?!this.initialDecodedProtocol||!!this.initialTxForceRaw:!this._pronto.trim()||null===this._validation||!this._validation.recognized_protocol}get _dittoDisabledTooltip(){return this._isCommand&&this.initialDecodedProtocol&&this.initialTxForceRaw?$e("editor.ditto_disabled_cmd"):$e("editor.ditto_disabled")}firstUpdated(){this._pronto=this.initialPronto,this._alias=this.initialAlias,this._sendCount=this.initialSendCount,this._ditto=this.initialDitto,this._pronto.trim()&&this._validate()}updated(){const e=this.shadowRoot?.querySelector("textarea");if(!e)return;const t=Math.round(.45*window.innerHeight);e.style.height="0px";const i=Math.min(Math.max(e.scrollHeight+2,64),t);e.style.height=`${i}px`}disconnectedCallback(){super.disconnectedCallback(),null!==this._debounce&&clearTimeout(this._debounce)}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_onSendCountInput(e){const t=parseInt(e.target.value,10);this._sendCount=Number.isNaN(t)?1:Math.max(1,Math.min(t,10))}_onDittoInput(e){const t=parseInt(e.target.value,10);this._ditto=Number.isNaN(t)?0:Math.max(0,Math.min(t,20))}_onProntoInput(e){this._pronto=e.target.value,null!==this._debounce&&clearTimeout(this._debounce),this._pronto.trim()?this._debounce=setTimeout(()=>{this._validate()},250):this._validation=null}_onKeydown(e){"Enter"!==e.key||e.shiftKey||(e.preventDefault(),this._canSave&&this._save())}async _validate(){try{this._validation=await this.api.validatePronto(this._pronto)}catch{this._validation=null}}_slPreview(){const e=this._validation?.normalized;if(!e)return null;const t=e.split(" ").map(e=>parseInt(e,16));if(t.length<5||t.some(e=>Number.isNaN(e)))return null;const i=[];for(const e of t.slice(4)){if(e>=1024)break;i.push(e<48?"S":"L")}return i.length?i:null}async _save(){if(!this._canSave)return;this._busy=!0,this._error=null;const e=this._dittoCountDisabled?void 0:this._ditto;try{if(this._isCommand){const t=await this.api.updateCommand({device_id:this.deviceId,command_id:this.commandId,name:this._alias.trim(),pronto:this._pronto,send_count:this._sendCount,repeat_count:e});this.dispatchEvent(new CustomEvent("command-edited",{detail:t,bubbles:!0,composed:!0}))}else if(null!==this.signalId){const t=await this.api.editSignalPronto({device_id:this.deviceId,signal_id:this.signalId,pronto:this._pronto,alias:this._alias.trim(),send_count:this._sendCount,repeat_count:e});this.dispatchEvent(new CustomEvent("signal-edited",{detail:t,bubbles:!0,composed:!0}))}else{const t=await this.api.createSignal({device_id:this.deviceId,pronto:this._pronto,alias:this._alias.trim()||void 0,send_count:this._sendCount,repeat_count:e});this.dispatchEvent(new CustomEvent("signal-created",{detail:t.signal,bubbles:!0,composed:!0}))}}catch(e){this._error=e.message}finally{this._busy=!1}}async _selectCode(){const e=this.shadowRoot?.querySelector("textarea");e&&(e.focus(),e.select());let t=!1;try{window.isSecureContext&&navigator.clipboard&&(await navigator.clipboard.writeText(this._pronto),t=!0)}catch{t=!1}this._copyHint=$e(t?"editor.copied":"editor.press_copy"),setTimeout(()=>{this._copyHint=null},2e3)}_renderFeedback(){const e=this._validation;if(!e)return"";const t=this._slPreview();return F`
            <div class="feedback">
                <div class="status ${e.valid?"ok":"bad"}">
                    <span class="mark">${e.valid?"✓":"✗"}</span>
                    ${e.valid?$e("editor.valid"):$e("editor.not_valid")}
                </div>
                ${e.valid?F`
                          <div class="metrics">
                              ${null!==e.frequency_khz?F`<span>${e.frequency_khz} kHz</span>`:""}
                              ${null!==e.burst_pair_count?F`<span
                                        >${ke("editor.burst_pair",e.burst_pair_count)}</span
                                    >`:""}
                              ${e.recognized_protocol?F`<span class="recognized"
                                        >${$e("editor.recognized_as",{protocol:e.recognized_protocol})}</span
                                    >`:""}
                          </div>
                          ${t?F`<div class="diamonds">
                                    ${t.map(e=>"L"===e?F`<span class="diamond long">◆</span>`:F`<span class="diamond short">◇</span>`)}
                                </div>`:""}
                      `:""}
                ${e.errors.map(e=>F`<div class="msg err">${e}</div>`)}
                ${e.warnings.map(e=>F`<div class="msg warn">${e}</div>`)}
            </div>
        `}get _carrierHz(){const e=this._validation?.valid?this._validation.frequency_khz:null;return null!=e?Math.round(1e3*e):null}get _showSnap(){if(!this.allowSnap)return!1;const e=this._carrierHz;return null!=e&&!(e=>Math.abs(e-Zi(e))<=500)(e)}async _snap(e){this._snapping=!0,this._error=null;try{const t=await this.api.snapPreview({pronto:this._pronto,target_frequency:e});this._pronto=t.pronto,await this._validate(),this._snapFlash=!0,setTimeout(()=>{this._snapFlash=!1},700)}catch(e){this._error=e.message}finally{this._snapping=!1}}_renderSnap(){if(!this._showSnap)return"";const e=this._carrierHz,t=Zi(e),i=(e/1e3).toFixed(1),s=(t/1e3).toFixed(0);return F`
            <div class="snap-notice">
                <div class="snap-text">
                    ${$e("editor.snap_notice",{khz:i})}
                </div>
                <button
                    class="snap-btn"
                    ?disabled=${this._snapping}
                    @click=${()=>this._snap(t)}
                >
                    ${this._snapping?$e("editor.snapping"):$e("editor.snap_to",{khz:s})}
                </button>
            </div>
        `}render(){const e=this._isCommand?$e("editor.edit_command"):this._isEdit?$e("editor.edit_signal"):$e("editor.create_signal"),t=this._isEdit?this._busy?$e("common.saving"):$e("common.save"):this._busy?$e("common.creating"):$e("common.create"),i=this._isEdit&&this.hasTrigger&&this._dirty,s=this._isCommand?$e("editor.trigger_note_cmd"):$e("editor.trigger_note_sig"),r=this._isCommand?$e("assign.command_name"):this._isEdit?$e("editor.alias_label"):$e("editor.alias_optional");return F`
            <ha-dialog
                open
                heading=${e}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?F`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <div class="field">
                    <label>${$e("editor.pronto_code")}</label>
                    <div class="code-wrap">
                        <textarea
                            class=${this._snapFlash?"snap-flash":""}
                            rows="4"
                            .value=${this._pronto}
                            placeholder="0000 006D ..."
                            autofocus
                            spellcheck="false"
                            @input=${this._onProntoInput}
                            @keydown=${this._onKeydown}
                        ></textarea>
                        ${this._pronto.trim()?F`
                                  ${this._copyHint?F`<span class="copy-flash"
                                            >${this._copyHint}</span
                                        >`:""}
                                  <button
                                      class="copy-icon"
                                      title=${$e("editor.select_all")}
                                      @click=${this._selectCode}
                                  >
                                      <ha-svg-icon
                                          .path=${"M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"}
                                      ></ha-svg-icon>
                                  </button>
                              `:""}
                    </div>
                </div>

                ${this._renderFeedback()} ${this._renderSnap()}

                <div class="field">
                    <label>${r}</label>
                    <input
                        type="text"
                        .value=${this._alias}
                        placeholder=${$e("editor.alias_placeholder")}
                        @input=${e=>this._alias=e.target.value}
                        @keydown=${this._onKeydown}
                    />
                </div>

                <div class="field tx-knobs">
                    <div class="knob">
                        <label>${$e("assign.send_times")}</label>
                        <input
                            class="num-input"
                            type="number"
                            min="1"
                            max="10"
                            .value=${String(this._sendCount)}
                            title=${$e("editor.send_times_title")}
                            @input=${this._onSendCountInput}
                            @keydown=${this._onKeydown}
                        />
                    </div>
                    ${this._dittoCountDisabled?"":F`<div class="knob">
                              <label>${$e("assign.ditto_count")}</label>
                              <input
                                  class="num-input"
                                  type="number"
                                  min="0"
                                  max="20"
                                  .value=${String(this._ditto)}
                                  title=${$e("editor.ditto_title")}
                                  @input=${this._onDittoInput}
                                  @keydown=${this._onKeydown}
                              />
                          </div>`}
                </div>
                ${this.initialObservedRepeatCount>0?F`<div class="observed-hint">
                          ${ke("editor.observed",this.initialObservedRepeatCount)}
                      </div>`:""}

                ${i?F`<div class="note">${s}</div>`:""}

                <div class="dialog-actions">
                    <span class="spacer"></span>
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${$e("common.cancel")}
                    </button>
                    <button
                        class="action-btn create-btn"
                        @click=${this._save}
                        ?disabled=${!this._canSave}
                    >
                        ${t}
                    </button>
                </div>
            </ha-dialog>
        `}};Wi.styles=[Fi,a`
        .field {
            display: block;
            margin: 12px 0;
            width: 100%;
        }
        .field label {
            display: block;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin-bottom: 6px;
        }
        input[type="text"],
        textarea {
            width: 100%;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.95rem;
            font-family: inherit;
            box-sizing: border-box;
        }
        textarea {
            font-family: monospace;
            resize: vertical;
            /* Extra top padding keeps the first line of code clear of the
               corner copy icon. */
            padding-top: 24px;
            /* updated() sizes the height to fit the code (clamped in JS), so
               a long Pronto scrolls instead of overflowing the dialog. */
            overflow-y: auto;
        }
        .code-wrap {
            position: relative;
        }
        .copy-icon {
            position: absolute;
            top: 6px;
            right: 8px;
            z-index: 2;
            display: inline-flex;
            align-items: center;
            padding: 2px;
            border: none;
            background: none;
            color: var(--secondary-text-color);
            cursor: pointer;
            opacity: 0.55;
            transition: opacity 150ms ease;
        }
        .copy-icon:hover {
            opacity: 0.9;
        }
        .copy-icon ha-svg-icon {
            --mdc-icon-size: 12px;
        }
        .copy-flash {
            position: absolute;
            top: 7px;
            right: 34px;
            z-index: 2;
            font-size: 0.72rem;
            white-space: nowrap;
            color: var(--secondary-text-color);
            background: var(--card-background-color);
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 1px 6px;
            pointer-events: none;
        }
        input[type="text"]:focus,
        textarea:focus {
            outline: none;
            border-color: #b87333;
        }
        .tx-knobs {
            display: flex;
            gap: 16px;
        }
        .knob {
            display: flex;
            flex-direction: column;
        }
        input.num-input {
            width: 80px;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.95rem;
            font-family: inherit;
            box-sizing: border-box;
        }
        input.num-input:focus {
            outline: none;
            border-color: #b87333;
        }
        input.num-input:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .observed-hint {
            margin: -4px 0 12px;
            font-size: 0.78rem;
            color: var(--secondary-text-color);
        }
        .hint {
            margin-top: 6px;
            font-size: 0.78rem;
            color: var(--secondary-text-color);
        }
        @keyframes snap-flash {
            0% {
                border-color: #ff9800;
                background: rgba(255, 152, 0, 0.18);
            }
            100% {
                border-color: var(--divider-color);
                background: var(--card-background-color);
            }
        }
        textarea.snap-flash {
            animation: snap-flash 700ms ease-out;
        }
        .snap-notice {
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 4px 0 12px;
            padding: 10px 12px;
            border-radius: 6px;
            background: rgba(255, 152, 0, 0.1);
            border: 1px solid rgba(255, 152, 0, 0.35);
        }
        .snap-text {
            flex: 1;
            font-size: 0.8rem;
            line-height: 1.3;
            color: #b26500;
        }
        .snap-btn {
            flex-shrink: 0;
            background: none;
            border: 1px solid #e65100;
            color: #e65100;
            border-radius: 4px;
            padding: 6px 12px;
            font-size: 0.8rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            transition: background 150ms ease;
        }
        .snap-btn:hover:not(:disabled) {
            background: rgba(255, 152, 0, 0.12);
        }
        .snap-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        ha-alert {
            display: block;
            margin: 8px 0;
        }
        .feedback {
            margin: 4px 0 12px;
            padding: 10px 12px;
            border-radius: 6px;
            background: var(--secondary-background-color);
        }
        .status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.9rem;
            font-weight: 500;
        }
        .status .mark {
            font-size: 1rem;
        }
        .status.ok {
            color: #2e7d32;
        }
        .status.bad {
            color: #e65100;
        }
        .metrics {
            display: flex;
            gap: 14px;
            margin-top: 6px;
            font-size: 0.8rem;
            color: var(--secondary-text-color);
        }
        .recognized {
            color: #2e7d32;
        }
        .diamonds {
            display: flex;
            flex-wrap: wrap;
            gap: 1px;
            margin-top: 8px;
            line-height: 1;
        }
        .diamond {
            font-size: 0.7rem;
        }
        .diamond.long {
            color: var(--primary-color);
        }
        .diamond.short {
            color: var(--warning-color, #ff9800);
        }
        .msg {
            margin-top: 6px;
            font-size: 0.8rem;
        }
        .msg.err {
            color: #e65100;
        }
        .msg.warn {
            color: #b89930;
        }
        .note {
            margin: 4px 0 12px;
            padding: 8px 10px;
            border-radius: 6px;
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            background: var(--secondary-background-color);
        }
        /* Left-aligned actions row (a spacer pushes the main buttons
           right so Delete can sit flush left); ships this way. */
        .dialog-actions {
            align-items: center;
            justify-content: flex-start;
        }
        .spacer {
            flex: 1;
        }
        .copy-btn {
            background: transparent;
            color: var(--secondary-text-color);
        }
        .copy-btn:hover:not(:disabled) {
            background: var(--secondary-background-color);
        }
        .create-btn {
            background: #b87333;
            color: #fff;
            border-color: #b87333;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `],e([pe({attribute:!1})],Wi.prototype,"api",void 0),e([pe({attribute:!1})],Wi.prototype,"deviceId",void 0),e([pe({attribute:!1})],Wi.prototype,"signalId",void 0),e([pe({attribute:!1})],Wi.prototype,"commandId",void 0),e([pe({attribute:!1})],Wi.prototype,"initialPronto",void 0),e([pe({attribute:!1})],Wi.prototype,"initialAlias",void 0),e([pe({attribute:!1})],Wi.prototype,"initialSendCount",void 0),e([pe({attribute:!1})],Wi.prototype,"initialDitto",void 0),e([pe({attribute:!1})],Wi.prototype,"initialObservedRepeatCount",void 0),e([pe({attribute:!1})],Wi.prototype,"initialTxForceRaw",void 0),e([pe({attribute:!1})],Wi.prototype,"initialDecodedProtocol",void 0),e([pe({type:Boolean})],Wi.prototype,"hasTrigger",void 0),e([pe({type:Boolean})],Wi.prototype,"allowSnap",void 0),e([he()],Wi.prototype,"_pronto",void 0),e([he()],Wi.prototype,"_alias",void 0),e([he()],Wi.prototype,"_sendCount",void 0),e([he()],Wi.prototype,"_ditto",void 0),e([he()],Wi.prototype,"_busy",void 0),e([he()],Wi.prototype,"_error",void 0),e([he()],Wi.prototype,"_validation",void 0),e([he()],Wi.prototype,"_copyHint",void 0),e([he()],Wi.prototype,"_snapping",void 0),e([he()],Wi.prototype,"_snapFlash",void 0),Wi=e([me("ir-signal-editor")],Wi);let Yi=class extends ne{constructor(){super(...arguments),this.value=[],this.disabled=!1,this._receivers=[],this._receiversLoaded=!1}updated(e){super.updated(e),e.has("api")&&this.api&&!this._receiversLoaded&&(this._receiversLoaded=!0,this._loadReceivers())}async _loadReceivers(){if(this.api)try{this._receivers=await this.api.listReceivers()}catch{this._receivers=[]}}_receiverName(e){const t=this._receivers.find(t=>t.entity_id===e);return t?.name??e}_onAdd(e){const t=e.target,i=t.value;i&&(t.value="",this.value.includes(i)||this._fireChange([...this.value,i]))}_onRemove(e){this._fireChange(this.value.filter(t=>t!==e))}_fireChange(e){this.value=e,this.dispatchEvent(new CustomEvent("receivers-changed",{detail:{value:e},bubbles:!0,composed:!0}))}render(){const e=this._receivers.filter(e=>!this.value.includes(e.entity_id));return F`
            <label>${$e("picker.receivers_label")}</label>

            ${this.value.length>0?F`
                      <div class="chips">
                          ${this.value.map(e=>F`
                                  <span class="chip">
                                      <span class="chip-name"
                                          >${this._receiverName(e)}</span
                                      >
                                      ${this.disabled?"":F`<button
                                                class="chip-remove"
                                                @click=${()=>this._onRemove(e)}
                                                title=${$e("common.remove")}
                                            >
                                                &times;
                                            </button>`}
                                  </span>
                              `)}
                      </div>
                  `:""}

            ${0===this._receivers.length?F`<div class="no-receivers">${$e("picker.no_receivers")}</div>`:e.length>0?F`
                        <select @change=${this._onAdd} ?disabled=${this.disabled}>
                            <option value="">${$e("picker.add_receiver")}</option>
                            ${e.map(e=>F`
                                    <option value=${e.entity_id}>
                                        ${e.name}
                                    </option>
                                `)}
                        </select>
                    `:F`<div class="all-selected">${$e("picker.all_receivers_selected")}</div>`}
        `}};Yi.styles=a`
        :host {
            display: block;
        }
        label {
            display: var(--picker-label-display, block);
            font-size: 0.82rem;
            font-weight: 500;
            color: var(--primary-text-color);
            margin-bottom: 6px;
        }
        .chips {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 8px;
        }
        .chip {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: var(--secondary-background-color);
            color: var(--primary-color);
            font-size: 0.82rem;
            font-weight: 500;
            padding: 4px 8px;
            border-radius: 4px;
            line-height: 1;
        }
        .chip-name {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 200px;
        }
        .chip-remove {
            background: none;
            border: none;
            color: inherit;
            font-size: 1rem;
            cursor: pointer;
            padding: 0 2px;
            line-height: 1;
            opacity: 0.65;
            transition: opacity 120ms ease;
        }
        .chip-remove:hover {
            opacity: 1;
        }
        select {
            width: 100%;
            padding: 6px 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-family: inherit;
            font-size: 0.85rem;
        }
        .no-receivers,
        .all-selected {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
    `,e([pe({attribute:!1})],Yi.prototype,"api",void 0),e([pe({attribute:!1})],Yi.prototype,"value",void 0),e([pe({type:Boolean})],Yi.prototype,"disabled",void 0),e([he()],Yi.prototype,"_receivers",void 0),Yi=e([me("ir-receiver-picker")],Yi);let Gi=class extends ne{constructor(){super(...arguments),this.signalFingerprint="",this.protocol=null,this.code=null,this.slPattern=null,this.alias=null,this.byteHash=null,this.decodedFingerprint=null,this.sourceDeviceId=null,this.sourceCommandId=null,this.trigger=null,this.mirrorContext=!1,this._name="",this._minHits=1,this._receiverIds=[],this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this.trigger&&(this._name=this.trigger.name,this._minHits=this.trigger.min_hits,this._receiverIds=[...this.trigger.receiver_entity_ids??[]])}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _save(){const e=this._name.trim();if(e){this._busy=!0,this._error=null;try{let t;if(this.trigger)t=await this.api.updateTrigger(this.trigger.id,{name:e,min_hits:this._minHits,receiver_entity_ids:this._receiverIds});else{const i={name:e,protocol:this.protocol,code:this.code,min_hits:this._minHits,source_device_id:this.sourceDeviceId,source_command_id:this.sourceCommandId,receiver_entity_ids:this._receiverIds};this.signalFingerprint&&(i.signal_fingerprint=this.signalFingerprint),this.byteHash&&(i.byte_hash=this.byteHash),this.decodedFingerprint&&(i.decoded_fingerprint=this.decodedFingerprint),t=await this.api.createTrigger(i)}this.dispatchEvent(new CustomEvent("trigger-saved",{detail:t,bubbles:!0,composed:!0}))}catch(e){this._error=e.message??$e("trigger.save_failed")}finally{this._busy=!1}}else this._error=$e("common.name_required")}_emitDelete(){this.trigger&&this.dispatchEvent(new CustomEvent("trigger-delete",{detail:{triggerId:this.trigger.id},bubbles:!0,composed:!0}))}_prontoSlArray(e){const t=e.trim().split(/\s+/);if(t.length<6)return null;const i=parseInt(t[2],16)+parseInt(t[3],16),s=t.slice(4);if(s.length<2*i)return null;const r=[];for(let e=0;e<2*i;e++){const t=parseInt(s[e],16);r.push(t>=48)}return r.length>0?r:null}_renderSignalInfo(){const e=!!this.trigger;if(!e&&this.alias)return F`<span class="alias-inline"
                ><span class="alias-tag">${$e("trigger.alias_tag")}</span
                ><span class="alias-name">${this.alias}</span></span
            >`;const t=e?null:this.slPattern;if(t)return F`<span class="diamonds">${[...t].map(e=>"L"===e?F`<span class="diamond long">&#9670;</span>`:F`<span class="diamond short">&#9671;</span>`)}</span>`;const i=e?this.trigger.code:this.code,s=e?this.trigger.protocol:this.protocol;if("PRONTO"===s?.toUpperCase()&&i){const e=this._prontoSlArray(i);if(e)return F`<span class="diamonds">${e.map(e=>e?F`<span class="diamond long">&#9670;</span>`:F`<span class="diamond short">&#9671;</span>`)}</span>`}return F`<span class="proto">${$e("trigger.event")}</span>`}render(){const e=!!this.trigger;return F`
            <div class="overlay" @click=${this._close}>
                <div class="dialog" @click=${e=>e.stopPropagation()}>
                    <h3 class="heading">
                        ${$e(e?"trigger.edit_heading":"trigger.create_heading")}
                    </h3>

                    <!-- Signal info (read-only) -->
                    <div class="signal-info">
                        ${this._renderSignalInfo()}
                    </div>

                    ${this.mirrorContext?F`<p class="field-hint scope-hint">
                              ${$e("trigger.mirror_hint")}
                          </p>`:""}

                    <!-- Name -->
                    <label class="field-label">${$e("trigger.name_label")}</label>
                    <input
                        class="field-input"
                        type="text"
                        placeholder=${$e("trigger.name_placeholder")}
                        .value=${this._name}
                        @input=${e=>{this._name=e.target.value}}
                        ?disabled=${this._busy}
                    />

                    <!-- Min Hits -->
                    <label class="field-label">
                        ${$e("trigger.min_hits")}
                        <span class="field-hint">
                            ${$e("trigger.min_hits_hint")}
                        </span>
                    </label>
                    <input
                        class="field-input hits-input"
                        type="number"
                        min="1"
                        max="10"
                        .value=${String(this._minHits)}
                        @input=${e=>{const t=parseInt(e.target.value,10);t>=1&&t<=10&&(this._minHits=t)}}
                        ?disabled=${this._busy}
                    />

                    <!-- Receiver scope -->
                    <div class="receiver-field">
                        <ir-receiver-picker
                            .api=${this.api}
                            .value=${this._receiverIds}
                            ?disabled=${this._busy}
                            @receivers-changed=${e=>{this._receiverIds=e.detail.value}}
                        ></ir-receiver-picker>
                        <p class="field-hint scope-hint">
                            ${$e("trigger.scope_hint")}
                        </p>
                    </div>

                    ${this._error?F`<p class="error">${this._error}</p>`:""}

                    <div class="actions">
                        ${e?F`<button
                                  class="btn delete-btn"
                                  @click=${this._emitDelete}
                                  ?disabled=${this._busy}
                              >${$e("common.delete")}</button>`:""}
                        <span class="actions-spacer"></span>
                        <button
                            class="btn cancel"
                            @click=${this._close}
                            ?disabled=${this._busy}
                        >${$e("common.cancel")}</button>
                        <button
                            class="btn save"
                            @click=${this._save}
                            ?disabled=${this._busy||!this._name.trim()}
                        >${this._busy?$e("common.saving"):$e(e?"common.update":"common.create")}</button>
                    </div>
                </div>
            </div>
        `}};Gi.styles=[Fi,a`
        .signal-info {
            padding: 8px 12px;
            background: var(--secondary-background-color);
            border-radius: 6px;
            margin-bottom: 16px;
            font-family: var(--code-font-family, monospace);
            font-size: 0.85rem;
            color: var(--secondary-text-color);
        }
        .proto {
            text-transform: uppercase;
            font-weight: 500;
        }
        .alias-inline {
            display: inline-flex;
            align-items: baseline;
            gap: 7px;
        }
        .alias-tag {
            font-size: 0.6rem;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            color: #ba7517;
        }
        .alias-name {
            font-size: 0.9rem;
            color: var(--primary-color);
        }
        .diamonds {
            display: inline-flex;
            gap: 1px;
            flex-wrap: wrap;
            line-height: 1;
        }
        .diamond {
            font-size: 0.7rem;
        }
        .diamond.long {
            color: var(--primary-color);
        }
        .diamond.short {
            color: var(--warning-color, #ff9800);
        }
        .field-label {
            display: block;
            font-size: 0.82rem;
            font-weight: 500;
            color: var(--primary-text-color);
            margin-bottom: 4px;
        }
        .field-hint {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.78rem;
            margin-left: 4px;
        }
        .field-input {
            display: block;
            width: 100%;
            box-sizing: border-box;
            padding: 8px 10px;
            border: 1px solid var(--divider-color);
            border-radius: 6px;
            font-size: 0.9rem;
            font-family: inherit;
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color);
            margin-bottom: 14px;
            outline: none;
            transition: border-color 150ms ease;
        }
        .field-input:focus {
            border-color: var(--primary-color);
        }
        .field-input:disabled {
            opacity: 0.5;
        }
        .hits-input {
            width: 80px;
        }
        .receiver-field {
            margin-bottom: 14px;
        }
        .scope-hint {
            margin: 6px 0 0;
            margin-left: 0;
        }
        .error {
            color: #e65100;
            font-size: 0.85rem;
            margin: 0 0 12px;
        }
        .actions {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 4px;
        }
        .actions-spacer {
            flex: 1;
        }
        .btn {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 6px;
            padding: 8px 20px;
            font-size: 0.85rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            transition: background 150ms ease;
        }
        .btn:hover {
            background: var(--secondary-background-color);
        }
        .btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .cancel {
            color: var(--secondary-text-color);
        }
        .save {
            color: #fff;
            background: #b89930;
            border-color: #b89930;
        }
        .save:hover {
            background: #a08328;
        }
        .delete-btn {
            color: #e65100;
            border-color: rgba(230, 81, 0, 0.3);
        }
        .delete-btn:hover {
            background: rgba(230, 81, 0, 0.08);
        }
    `],e([pe({attribute:!1})],Gi.prototype,"api",void 0),e([pe()],Gi.prototype,"signalFingerprint",void 0),e([pe()],Gi.prototype,"protocol",void 0),e([pe()],Gi.prototype,"code",void 0),e([pe()],Gi.prototype,"slPattern",void 0),e([pe()],Gi.prototype,"alias",void 0),e([pe()],Gi.prototype,"byteHash",void 0),e([pe()],Gi.prototype,"decodedFingerprint",void 0),e([pe()],Gi.prototype,"sourceDeviceId",void 0),e([pe()],Gi.prototype,"sourceCommandId",void 0),e([pe({attribute:!1})],Gi.prototype,"trigger",void 0),e([pe({type:Boolean})],Gi.prototype,"mirrorContext",void 0),e([he()],Gi.prototype,"_name",void 0),e([he()],Gi.prototype,"_minHits",void 0),e([he()],Gi.prototype,"_receiverIds",void 0),e([he()],Gi.prototype,"_busy",void 0),e([he()],Gi.prototype,"_error",void 0),Gi=e([me("ir-trigger-dialog")],Gi);const Ki=a`
    .action-popover {
        position: fixed;
        z-index: 50;
        min-width: 200px;
        max-width: 280px;
        background: var(--card-background-color, #1c1c1c);
        border: 1px solid var(--divider-color);
        border-radius: 6px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
        padding: 4px 0;
        overflow: auto;
        max-height: 320px;
    }
    .popover-header {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--secondary-text-color);
        padding: 6px 12px 4px;
    }
    .popover-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        width: 100%;
        padding: 7px 12px;
        background: none;
        border: none;
        color: var(--primary-text-color);
        font-size: 0.82rem;
        font-family: inherit;
        cursor: pointer;
        text-align: left;
        transition: background 100ms ease;
    }
    .popover-item:hover {
        background: var(--secondary-background-color);
    }
    .popover-item.active {
        color: var(--primary-color);
        font-weight: 500;
    }
    .popover-item.clear {
        color: var(--secondary-text-color);
        font-style: italic;
        border-bottom: 1px solid var(--divider-color);
        margin-bottom: 2px;
    }
    .popover-check {
        color: var(--primary-color);
        font-size: 0.9rem;
    }
    .popover-existing {
        font-size: 0.72rem;
        color: var(--secondary-text-color);
        font-style: italic;
        margin-left: 8px;
        flex-shrink: 0;
    }
    /* Trigger-popover extras (v0.5.7) */
    .popover-item.accent {
        color: var(--primary-color);
        font-weight: 500;
    }
    .popover-divider {
        height: 1px;
        background: var(--divider-color);
        margin: 2px 0;
    }
    .popover-row {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        gap: 2px;
        min-width: 0;
    }
    .popover-name {
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 240px;
    }
    .popover-scope {
        font-size: 0.7rem;
        color: var(--secondary-text-color);
    }
`;let Ji=class extends ne{constructor(){super(...arguments),this.triggers=[],this.receivers=[],this.top=0,this.left=0}render(){return F`
            <div
                class="action-popover"
                style="top:${this.top}px; left:${this.left}px"
            >
                <div class="popover-header">${$e("popover.triggers")}</div>
                <button
                    class="popover-item accent"
                    @click=${()=>this._emit("create-new")}
                >
                    <span>${$e("popover.new_trigger")}</span>
                </button>
                <div class="popover-divider"></div>
                ${this.triggers.map(e=>F`
                        <button
                            class="popover-item"
                            @click=${()=>this._emit("edit-trigger",e)}
                        >
                            <span class="popover-row">
                                <span class="popover-name">${e.name}</span>
                                <span class="popover-scope"
                                    >${this._renderScope(e)}</span
                                >
                            </span>
                        </button>
                    `)}
            </div>
        `}_renderScope(e){const t=e.receiver_entity_ids??[];return 0===t.length?$e("popover.any_receiver"):1===t.length?this._friendly(t[0]):$e("popover.n_more",{name:this._friendly(t[0]),count:t.length-1})}_friendly(e){const t=this.receivers.find(t=>t.entity_id===e);return t?.name??e}_emit(e,t){this.dispatchEvent(new CustomEvent(e,{detail:t,bubbles:!0,composed:!0}))}};Ji.styles=[Ki,a`
            :host {
                display: contents;
            }
        `],e([pe({attribute:!1})],Ji.prototype,"triggers",void 0),e([pe({attribute:!1})],Ji.prototype,"receivers",void 0),e([pe({type:Number})],Ji.prototype,"top",void 0),e([pe({type:Number})],Ji.prototype,"left",void 0),Ji=e([me("ir-trigger-popover")],Ji);const Qi=[{value:"media_player",label:"Media Player"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"light",label:"Light"},{value:"switch",label:"Switch"},{value:"screen",label:"Screen / Shade"},{value:"other",label:"Other"}];let es=class extends ne{constructor(){super(...arguments),this._busy=!1,this._captureName=null,this._toast=null,this._confirmDelete=!1,this._commandToDelete=null,this._editCommand=null,this._actionOptions=[],this._mappingCommandName=null,this._popoverTop=0,this._popoverLeft=0,this._customActionOpen=!1,this._customActionValue="",this._dismissHandler=null,this._editingName=!1,this._draftName="",this._triggers=[],this._triggerCommand=null,this._triggerEdit=null,this._confirmDeleteTriggerId=null,this._triggerPopover=null,this._receivers=[],this._sortable=null,this._pendingReorderTimeout=null,this._commandsListVersion=0,this._onDocClickForTriggerPopover=e=>{const t=this.shadowRoot?.querySelector("ir-trigger-popover");t&&e.composedPath().includes(t)||this._closeTriggerPopover()},this._onScrollForTriggerPopover=()=>{this._closeTriggerPopover()}}_emitterName(e){const t=this.hass?.states?.[e];return t?.attributes?.friendly_name??e}_deviceRegistryName(e){const t=this.hass?.devices?.[e];return t?.name_by_user??t?.name??e}_deviceConfigEntryId(e){const t=this.hass?.devices?.[e];return t?(t.config_entries??[])[0]??null:null}_configEntryDomain(e){const t=this.hass?.config_entries?.entries?.[e];return t?.domain??null}_integrationUrl(e){if(!e)return null;const t=this._configEntryDomain(e);return t?`/config/integrations/integration/${t}`:null}_entityIntegrationUrl(e){const t=e.split(".")[0],i=this.hass?.entities?.[e];return i?.config_entry_id?this._integrationUrl(i.config_entry_id):i?.platform?`/config/integrations/integration/${i.platform}`:`/config/integrations/integration/${t}`}async _refresh(){this.device=await this.api.getDevice(this.device.id),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}_flash(e){this._toast=e,setTimeout(()=>{this._toast=null},2400)}_startEditName(){this._draftName=this.device.name,this._editingName=!0,this.updateComplete.then(()=>{const e=this.shadowRoot?.querySelector(".name-input");e?.focus(),e?.select()})}async _saveName(){const e=this._draftName.trim();if(e&&e!==this.device.name){this._busy=!0;try{this.device=await this.api.updateDevice(this.device.id,{name:e}),this._flash($e("devdetail.name_updated")),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Update failed: ${e.message}`)}finally{this._busy=!1,this._editingName=!1}}else this._editingName=!1}_onNameKeyDown(e){"Enter"===e.key?(e.preventDefault(),this._saveName()):"Escape"===e.key&&(this._editingName=!1)}async _onTypeChanged(e){const t=e.target.value;if(t!==this.device.device_type){this._busy=!0;try{this.device=await this.api.updateDevice(this.device.id,{device_type:t}),this._flash($e("devdetail.type_updated")),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Update failed: ${e.message}`)}finally{this._busy=!1}}}async _onEmittersChanged(e){const t=e.detail.value,i=[...this.device.emitter_entity_ids];this.device={...this.device,emitter_entity_ids:t},this._busy=!0;try{this.device=await this.api.updateDevice(this.device.id,{emitter_entity_ids:t}),this._flash($e("devdetail.emitters_updated")),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this.device={...this.device,emitter_entity_ids:i},this._flash(`Update failed: ${e.message}`)}finally{this._busy=!1}}connectedCallback(){super.connectedCallback(),this._loadActionOptions(),this._loadTriggers(),this.api.listReceivers().then(e=>{this._receivers=e}).catch(()=>{this._receivers=[]})}updated(e){e.has("device")&&(this._loadActionOptions(),this._loadTriggers()),e.has("_commandsListVersion")&&!this._sortable&&this._attachSortable()}async _loadActionOptions(){try{this._actionOptions=await this.api.getActionOptions(this.device.device_type)}catch{this._actionOptions=[]}}async _loadTriggers(){try{this._triggers=await this.api.listTriggers()}catch{this._triggers=[]}}_commandHasTrigger(e){return this._triggers.some(t=>t.source_command_id===e.id)}_commandTriggerCount(e){return this._triggers.filter(t=>t.source_command_id===e.id).length}_onToggleTrigger(e){const t=e.detail?.command;if(!t)return;const i=this._triggers.filter(e=>e.source_command_id===t.id);if(0===i.length)return void(this._triggerCommand=t);const s=e.detail?.buttonRect;this._triggerPopover={command:t,top:s?s.bottom+4:120,left:s?Math.max(8,s.right-220):120},this._installTriggerPopoverDismiss()}_triggersForCommand(e){return this._triggers.filter(t=>t.source_command_id===e.id)}_closeTriggerPopover(){this._triggerPopover=null,this._removeTriggerPopoverDismiss()}_onTriggerPopoverCreateNew(){const e=this._triggerPopover;this._closeTriggerPopover(),e&&(this._triggerCommand=e.command)}_onTriggerPopoverEdit(e){const t=e.detail;this._closeTriggerPopover(),t&&(this._triggerEdit=t)}_installTriggerPopoverDismiss(){setTimeout(()=>{document.addEventListener("click",this._onDocClickForTriggerPopover,!0),window.addEventListener("scroll",this._onScrollForTriggerPopover,!0)},0)}_removeTriggerPopoverDismiss(){document.removeEventListener("click",this._onDocClickForTriggerPopover,!0),window.removeEventListener("scroll",this._onScrollForTriggerPopover,!0)}_closeTriggerDialog(){this._triggerCommand=null,this._triggerEdit=null}async _onTriggerSaved(){this._triggerCommand=null,this._triggerEdit=null,await this._loadTriggers(),this.dispatchEvent(new CustomEvent("trigger-changed",{bubbles:!0,composed:!0}))}_requestDeleteTrigger(e){this._confirmDeleteTriggerId=e}async _doDeleteTrigger(){if(!this._confirmDeleteTriggerId)return;const e=this._confirmDeleteTriggerId;this._confirmDeleteTriggerId=null,this._triggerEdit=null;try{await this.api.deleteTrigger(e),await this._loadTriggers(),this.dispatchEvent(new CustomEvent("trigger-changed",{bubbles:!0,composed:!0}))}catch{}}_getActionLabel(e){const t=this.device.entity_config?.command_mapping??{};for(const[i,s]of Object.entries(t))if(s.toLowerCase()===e.toLowerCase()){const e=this._actionOptions.find(e=>e.key===i);return e?we(e.label):i}return null}_onMapAction(e){const{command:t}=e.detail;if(!t)return;const i=e.target.shadowRoot?.querySelector(".badge-btn");if(i){const e=i.getBoundingClientRect();this._popoverTop=e.bottom+4,this._popoverLeft=Math.max(8,e.right-220)}this._mappingCommandName=t.name,requestAnimationFrame(()=>{this._dismissHandler=e=>{const t=e.composedPath(),i=this.shadowRoot?.querySelector(".action-popover");i&&!t.includes(i)&&this._closePopover()},document.addEventListener("click",this._dismissHandler,!0)})}_closePopover(){this._mappingCommandName=null,this._customActionOpen=!1,this._customActionValue="",this._dismissHandler&&(document.removeEventListener("click",this._dismissHandler,!0),this._dismissHandler=null)}disconnectedCallback(){super.disconnectedCallback(),this._dismissHandler&&(document.removeEventListener("click",this._dismissHandler,!0),this._dismissHandler=null),this._removeTriggerPopoverDismiss(),this._sortable?.destroy(),this._sortable=null,this._cancelPendingReorderSave()}firstUpdated(){this._attachSortable()}_attachSortable(){if(this._sortable)return;const e=this.renderRoot.querySelector(".commands-list");e&&(this._sortable=bi.create(e,{handle:".grip-handle",animation:150,ghostClass:"sortable-ghost",onEnd:e=>{const t=e.oldIndex,i=e.newIndex;if(void 0===t||void 0===i||t===i)return;const s=[...this.device.commands],[r]=s.splice(t,1);s.splice(i,0,r),this.device={...this.device,commands:s},this.dispatchEvent(new CustomEvent("commands-reordered",{detail:{commands:s},bubbles:!0,composed:!0})),this._sortable?.destroy(),this._sortable=null;const o=this.renderRoot.querySelector(".commands-list");if(o)for(const e of Array.from(o.querySelectorAll("ir-command-row")))e.remove();this._commandsListVersion++,this._scheduleReorderSave(s.map(e=>e.id))}}))}_scheduleReorderSave(e){this._cancelPendingReorderSave(),this._pendingReorderTimeout=window.setTimeout(async()=>{this._pendingReorderTimeout=null;try{await this.api.reorderCommands(this.device.id,e)}catch(e){this._flash($e("devdetail.reorder_failed",{message:e.message})),await this._refresh()}},500)}_cancelPendingReorderSave(){null!==this._pendingReorderTimeout&&(clearTimeout(this._pendingReorderTimeout),this._pendingReorderTimeout=null)}_getCommandForAction(e){return(this.device.entity_config?.command_mapping??{})[e]??null}async _selectAction(e,t){this._closePopover(),this._busy=!0;try{const i=await this.api.updateMapping(this.device.id,e,t);this.device={...this.device,entity_config:{...this.device.entity_config,command_mapping:i.mapping}},this._flash(t?$e("devdetail.mapped_to",{action:t}):$e("devdetail.mapping_cleared")),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this._flash($e("devdetail.mapping_failed",{message:e.message}))}finally{this._busy=!1}}_getCurrentActionKey(e){const t=this.device.entity_config?.command_mapping??{};for(const[i,s]of Object.entries(t))if(s.toLowerCase()===e.toLowerCase())return i;return""}async _onTest(e){const{command:t}=e.detail;if(t){this._busy=!0;try{await this.api.sendCommand(this.device.id,t.id),this._flash($e("devdetail.sent_cmd",{name:t.name}))}catch(e){this._flash($e("devdetail.send_failed",{message:e.message}))}finally{this._busy=!1}}}async _onToggleTxRaw(e){const{command:t}=e.detail;if(!t)return;const i=!t.tx_force_raw;this._busy=!0;try{await this.api.setCommandTxForceRaw(this.device.id,t.id,i),t.tx_force_raw=i,this.requestUpdate(),this._flash(i?`"${t.name}" will transmit the captured timings`:`"${t.name}" will transmit clean decoded timings`)}catch(e){this._flash(`Update failed: ${e.message}`)}finally{this._busy=!1}}_onDelete(e){const{command:t}=e.detail;t&&(this._commandToDelete=t)}_onEditCommand(e){const{command:t}=e.detail;t&&(this._editCommand=t)}async _onCommandEdited(e){const t=e.detail;this._editCommand=null,await this._refresh();const i=t.triggers?.rewired??[];if(i.length){const e=i.map(e=>`"${e}"`).join(", ");this._flash($e("devdetail.cmd_updated_repointed",{names:e}))}else this._flash($e("devdetail.cmd_updated"));this.dispatchEvent(new CustomEvent("trigger-changed",{bubbles:!0,composed:!0}))}async _onRenameCommand(e){const{command:t,name:i}=e.detail;this._busy=!0;try{const e=await this.api.updateCommand({device_id:this.device.id,command_id:t.id,name:i});await this._refresh();const s=e.mappings_updated;this._flash(s>0?`Renamed (updated ${s} action mapping${1===s?"":"s"})`:"Renamed"),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this._flash($e("devdetail.rename_failed",{message:e.message}))}finally{this._busy=!1}}async _confirmCommandDelete(){const e=this._commandToDelete;if(e){this._commandToDelete=null,this._cancelPendingReorderSave(),this._busy=!0;try{await this.api.deleteCommand(this.device.id,e.id),await this._refresh(),this._flash($e("devdetail.removed",{name:e.name}))}catch(e){this._flash(`Delete failed: ${e.message}`)}finally{this._busy=!1}}}_onCaptureClosed(){this._captureName=null}async _onCommandSaved(e){const{commandName:t}=e.detail;this._cancelPendingReorderSave(),await this._refresh(),this._flash($e("devdetail.saved",{name:t})),this._captureName=null}_goToSniffer(){this.dispatchEvent(new CustomEvent("navigate-sniffer",{bubbles:!0,composed:!0}))}_goToClips(){this.dispatchEvent(new CustomEvent("navigate-clips",{bubbles:!0,composed:!0}))}_goToMirror(){this.dispatchEvent(new CustomEvent("navigate-mirror",{bubbles:!0,composed:!0}))}async _deleteDevice(){this._busy=!0;try{await this.api.deleteDevice(this.device.id),this.dispatchEvent(new CustomEvent("device-deleted",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Delete failed: ${e.message}`)}finally{this._busy=!1,this._confirmDelete=!1}}_navigateIntegration(e){e&&(window.history.pushState(null,"",e),window.dispatchEvent(new PopStateEvent("popstate")))}render(){const e=this.device.commands,t=e.length;return F`
            <!-- Header: editable name + delete -->
            <section class="header">
                <div class="header-left">
                    ${this._editingName?F`
                              <input
                                  class="name-input"
                                  type="text"
                                  .value=${this._draftName}
                                  @input=${e=>this._draftName=e.target.value}
                                  @blur=${this._saveName}
                                  @keydown=${this._onNameKeyDown}
                                  ?disabled=${this._busy}
                              />
                          `:F`
                              <h1
                                  class="editable-name"
                                  @click=${this._startEditName}
                                  title=${$e("cmdrow.rename")}
                              >
                                  ${this.device.name}
                                  <span class="edit-icon">&#9998;</span>
                              </h1>
                          `}
                </div>
                <button
                    class="action-btn collapse-btn"
                    @click=${()=>this.dispatchEvent(new CustomEvent("collapse",{bubbles:!0,composed:!0}))}
                    title=${$e("common.close")}
                >&#x2715;</button>
            </section>

            <!-- Device metadata grid -->
            <div class="device-meta">
                <span class="meta-label">${$e("devdetail.type")}</span>
                <div class="meta-value">
                    <select
                        .value=${this.device.device_type}
                        @change=${this._onTypeChanged}
                        ?disabled=${this._busy}
                    >
                        ${Qi.map(e=>F`
                                <option
                                    value=${e.value}
                                    ?selected=${this.device.device_type===e.value}
                                >
                                    ${$e(`device_type.${e.value}`)}
                                </option>
                            `)}
                    </select>
                </div>
                <span class="meta-label">${$e("devlist.emitters")}</span>
                <div class="meta-value">
                    <ir-emitter-picker
                        .hass=${this.hass}
                        .api=${this.api}
                        .value=${this.device.emitter_entity_ids??[]}
                        ?disabled=${this._busy}
                        @emitters-changed=${this._onEmittersChanged}
                    ></ir-emitter-picker>
                </div>
            </div>

            <!-- Commands -->
            <div class="commands-section">
                <div class="commands-header">
                    <span>${$e("devdetail.commands",{count:t})}</span>
                </div>
                <div class="commands-list">
                    ${He(this._commandsListVersion,e.length>0?Ne(e,e=>e.id,e=>F`
                                      <ir-command-row
                                          data-id=${e.id}
                                          .templateName=${e.name}
                                          .command=${e}
                                          .busy=${this._busy}
                                          .actionLabel=${this._getActionLabel(e.name)}
                                          .hasTrigger=${this._commandHasTrigger(e)}
                                          .triggerCount=${this._commandTriggerCount(e)}
                                          .showActionMapping=${"other"!==this.device.device_type}
                                          @map-action=${this._onMapAction}
                                          @test=${this._onTest}
                                          @toggle-trigger=${this._onToggleTrigger}
                                          @toggle-tx-raw=${this._onToggleTxRaw}
                                          @edit-command=${this._onEditCommand}
                                          @rename-command=${this._onRenameCommand}
                                          @delete=${this._onDelete}
                                      >
                                          <ha-svg-icon
                                              slot="status"
                                              class="grip-handle"
                                              .path=${"M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z"}
                                              title=${$e("devdetail.drag")}
                                          ></ha-svg-icon>
                                      </ir-command-row>
                                  `):F`<div class="empty">${$e("devdetail.no_commands")}</div>`)}

                    ${this._mappingCommandName?F`
                              <div
                                  class="action-popover"
                                  style="top:${this._popoverTop}px; left:${this._popoverLeft}px"
                              >
                                  <div class="popover-header">${$e("devdetail.map_action")}</div>
                                  ${this._getCurrentActionKey(this._mappingCommandName)?F`
                                            <button
                                                class="popover-item clear"
                                                @click=${()=>this._selectAction(this._mappingCommandName,null)}
                                            >
                                                <span class="popover-label">${$e("devdetail.none_clear")}</span>
                                            </button>
                                        `:""}
                                  ${this._actionOptions.map(e=>{const t=this._getCurrentActionKey(this._mappingCommandName)===e.key,i=this._getCommandForAction(e.key),s=i&&i.toLowerCase()!==this._mappingCommandName.toLowerCase();return F`
                                          <button
                                              class="popover-item ${t?"active":""}"
                                              @click=${()=>this._selectAction(this._mappingCommandName,e.key)}
                                          >
                                              <span class="popover-label">${we(e.label)}</span>
                                              ${t?F`<span class="popover-check">&#10003;</span>`:s?F`<span class="popover-existing">${i}</span>`:""}
                                          </button>
                                      `})}
                                  ${this._customActionOpen?F`
                                            <div class="custom-action-row">
                                                <input
                                                    class="custom-action-input"
                                                    type="text"
                                                    placeholder=${$e("devdetail.custom_action_placeholder")}
                                                    .value=${this._customActionValue}
                                                    @input=${e=>this._customActionValue=e.target.value}
                                                    @keydown=${e=>{"Enter"===e.key&&this._customActionValue.trim()&&this._selectAction(this._mappingCommandName,this._customActionValue.trim())}}
                                                />
                                                <button
                                                    class="custom-action-set"
                                                    ?disabled=${!this._customActionValue.trim()}
                                                    @click=${()=>this._selectAction(this._mappingCommandName,this._customActionValue.trim())}
                                                >
                                                    ${$e("devdetail.set")}
                                                </button>
                                            </div>
                                        `:F`
                                            <button
                                                class="popover-item custom-action-open"
                                                @click=${e=>{e.stopPropagation(),this._customActionOpen=!0,this.updateComplete.then(()=>{this.shadowRoot?.querySelector(".custom-action-input")?.focus()})}}
                                            >
                                                <span class="popover-label"
                                                    >${$e("devdetail.custom_action")}</span
                                                >
                                            </button>
                                        `}
                              </div>
                          `:""}
                </div>
            </div>

            <div class="footer-actions">
                <div class="add-group">
                    <button
                        class="action-btn"
                        title=${$e("devdetail.sniff_title")}
                        @click=${this._goToSniffer}
                        ?disabled=${this._busy}
                    >${$e("devdetail.sniffed")}</button>
                    <button
                        class="action-btn"
                        title=${$e("devdetail.clip_title")}
                        @click=${this._goToClips}
                        ?disabled=${this._busy}
                    >${$e("devdetail.clipped")}</button>
                    <button
                        class="action-btn"
                        title=${$e("devdetail.mirror_title")}
                        @click=${this._goToMirror}
                        ?disabled=${this._busy}
                    >${$e("devdetail.mirrored")}</button>
                </div>
                <button
                    class="action-btn delete-btn"
                    @click=${()=>this._confirmDelete=!0}
                    ?disabled=${this._busy}
                >${$e("devlist.del_device_title")}</button>
            </div>

            <!-- Dialogs -->
            ${this._captureName?F`
                      <ir-capture-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .device=${this.device}
                          .commandName=${this._captureName}
                          @closed=${this._onCaptureClosed}
                          @command-saved=${this._onCommandSaved}
                      ></ir-capture-dialog>
                  `:""}
            ${this._confirmDelete?F`
                      <ir-confirm-dialog
                          title=${$e("devdetail.del_device_title",{name:this.device.name})}
                          message=${$e("devdetail.del_device_msg")}
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._deleteDevice}
                          @closed=${()=>this._confirmDelete=!1}
                      ></ir-confirm-dialog>
                  `:""}
            ${this._commandToDelete?F`
                      <ir-confirm-dialog
                          title=${$e("devdetail.del_cmd_title")}
                          message=${$e("devdetail.del_cmd_msg",{name:this._commandToDelete.name})}
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._confirmCommandDelete}
                          @closed=${()=>this._commandToDelete=null}
                      ></ir-confirm-dialog>
                  `:""}
            ${this._editCommand?F`
                      <ir-signal-editor
                          .api=${this.api}
                          .deviceId=${this.device.id}
                          .commandId=${this._editCommand.id}
                          .initialPronto=${this._editCommand.code??""}
                          .initialAlias=${this._editCommand.name}
                          .initialSendCount=${this._editCommand.send_count??1}
                          .initialDitto=${this._editCommand.repeat_count??1}
                          .initialTxForceRaw=${this._editCommand.tx_force_raw??!1}
                          .initialDecodedProtocol=${this._editCommand.decoded_protocol??null}
                          .hasTrigger=${this._commandHasTrigger(this._editCommand)}
                          @command-edited=${this._onCommandEdited}
                          @closed=${()=>this._editCommand=null}
                      ></ir-signal-editor>
                  `:""}
            ${this._triggerPopover?F`
                      <ir-trigger-popover
                          .triggers=${this._triggersForCommand(this._triggerPopover.command)}
                          .receivers=${this._receivers}
                          .top=${this._triggerPopover.top}
                          .left=${this._triggerPopover.left}
                          @create-new=${this._onTriggerPopoverCreateNew}
                          @edit-trigger=${this._onTriggerPopoverEdit}
                      ></ir-trigger-popover>
                  `:""}
            ${this._triggerCommand?F`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .protocol=${this._triggerCommand.protocol}
                          .code=${this._triggerCommand.code}
                          .byteHash=${this._triggerCommand.byte_hash??null}
                          .decodedFingerprint=${this._triggerCommand.decoded_fingerprint??null}
                          .sourceDeviceId=${this.device.id}
                          .sourceCommandId=${this._triggerCommand.id}
                          @trigger-saved=${this._onTriggerSaved}
                          @closed=${this._closeTriggerDialog}
                      ></ir-trigger-dialog>
                  `:""}
            ${this._triggerEdit?F`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .trigger=${this._triggerEdit}
                          @trigger-saved=${this._onTriggerSaved}
                          @closed=${this._closeTriggerDialog}
                          @trigger-delete=${e=>this._requestDeleteTrigger(e.detail.triggerId)}
                      ></ir-trigger-dialog>
                  `:""}
            ${this._confirmDeleteTriggerId?F`
                      <ir-confirm-dialog
                          title=${$e("mirror.del_trigger_title")}
                          message=${$e("devdetail.del_trigger_msg")}
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._doDeleteTrigger}
                          @closed=${()=>this._confirmDeleteTriggerId=null}
                      ></ir-confirm-dialog>
                  `:""}
            ${this._toast?F`<div class="toast" role="status">${this._toast}</div>`:""}
        `}};es.styles=[Vi,Ki,a`
        :host {
            display: block;
        }

        /* --- Header --- */
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
        }
        .header-left {
            flex: 1;
            min-width: 0;
        }
        h1 {
            font-size: 1.5rem;
            margin: 0;
        }
        .editable-name {
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            border-bottom: 1px dashed transparent;
            transition: border-color 150ms ease;
        }
        .editable-name:hover {
            border-bottom-color: var(--primary-color);
        }
        .edit-icon {
            font-size: 0.75rem;
            color: var(--secondary-text-color);
            opacity: 0;
            transition: opacity 150ms ease;
        }
        .editable-name:hover .edit-icon {
            opacity: 1;
        }
        .name-input {
            font-size: 1.5rem;
            font-family: inherit;
            font-weight: bold;
            border: none;
            border-bottom: 2px solid var(--primary-color);
            background: transparent;
            color: var(--primary-text-color);
            outline: none;
            width: 100%;
            padding: 0 0 2px;
        }
        .header .action-btn.collapse-btn {
            flex-shrink: 0;
            align-self: center;
        }

        /* --- Metadata grid --- */
        .device-meta {
            display: grid;
            grid-template-columns: 80px 1fr;
            gap: 8px 12px;
            align-items: start;
            margin: 16px 0 0;
        }
        .meta-label {
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--secondary-text-color);
            padding-top: 6px;
        }
        .meta-value select {
            width: 100%;
            padding: 6px 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-family: inherit;
            font-size: 0.85rem;
        }
        .meta-value ir-emitter-picker {
            --picker-label-display: none;
        }

        /* --- Buttons --- */
        .action-btn.collapse-btn {
            font-size: 1rem;
            padding: 2px 8px;
            color: var(--secondary-text-color);
            border-color: transparent;
        }
        .action-btn.collapse-btn:hover {
            color: var(--primary-text-color);
            background: var(--secondary-background-color);
        }

        /* --- Commands section (Sniffer-style) --- */
        .commands-section {
            margin: 16px 0;
            border-top: 1px solid var(--divider-color);
            padding-top: 12px;
        }
        .commands-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 8px;
            color: var(--primary-text-color);
        }
        .commands-list {
            display: flex;
            flex-direction: column;
        }
        /* --- Drag handle (slotted into ir-command-row's status column) --- */
        .grip-handle {
            --mdc-icon-size: 18px;
            color: var(--secondary-text-color);
            opacity: 0.6;
            cursor: grab;
            transition: opacity 120ms ease;
        }
        .grip-handle:hover {
            opacity: 1;
        }
        .grip-handle:active {
            cursor: grabbing;
        }
        /* SortableJS applies this class to the element being dragged. */
        ir-command-row.sortable-ghost {
            opacity: 0.4;
        }
        /* Action-popover styles live in the shared ir-popover-styles module
           (spread into static styles below) so ir-trigger-popover reuses the
           exact same treatment. */
        .empty {
            color: var(--secondary-text-color);
            font-style: italic;
            padding: 12px 0;
        }
        .footer-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 16px 0;
            flex-wrap: wrap;
            gap: 8px;
        }
        .add-group {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .add-label {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
        }

        /* --- Toast --- */
        .toast {
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            background: var(--primary-color);
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            z-index: 100;
        }

        /* Custom action entry (free-form key) inside the Map action
           popover. Input + Set on one row, matching popover chrome. */
        .custom-action-row {
            display: flex;
            gap: 6px;
            padding: 6px 10px 8px;
            align-items: center;
        }
        .custom-action-input {
            flex: 1;
            min-width: 0;
            padding: 5px 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.8rem;
            font-family: var(--code-font-family, monospace);
            box-sizing: border-box;
        }
        .custom-action-input:focus {
            outline: none;
            border-color: var(--primary-color);
        }
        .custom-action-set {
            border: 1px solid var(--divider-color);
            background: none;
            border-radius: 4px;
            padding: 5px 10px;
            font-size: 0.78rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            color: var(--primary-text-color);
        }
        .custom-action-set:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .custom-action-set:hover:not(:disabled) {
            background: var(--secondary-background-color);
        }
    `],e([pe({attribute:!1})],es.prototype,"api",void 0),e([pe({attribute:!1})],es.prototype,"hass",void 0),e([pe({attribute:!1})],es.prototype,"device",void 0),e([he()],es.prototype,"_busy",void 0),e([he()],es.prototype,"_captureName",void 0),e([he()],es.prototype,"_toast",void 0),e([he()],es.prototype,"_confirmDelete",void 0),e([he()],es.prototype,"_commandToDelete",void 0),e([he()],es.prototype,"_editCommand",void 0),e([he()],es.prototype,"_actionOptions",void 0),e([he()],es.prototype,"_mappingCommandName",void 0),e([he()],es.prototype,"_popoverTop",void 0),e([he()],es.prototype,"_popoverLeft",void 0),e([he()],es.prototype,"_customActionOpen",void 0),e([he()],es.prototype,"_customActionValue",void 0),e([he()],es.prototype,"_editingName",void 0),e([he()],es.prototype,"_draftName",void 0),e([he()],es.prototype,"_triggers",void 0),e([he()],es.prototype,"_triggerCommand",void 0),e([he()],es.prototype,"_triggerEdit",void 0),e([he()],es.prototype,"_confirmDeleteTriggerId",void 0),e([he()],es.prototype,"_triggerPopover",void 0),e([he()],es.prototype,"_receivers",void 0),e([he()],es.prototype,"_commandsListVersion",void 0),es=e([me("ir-device-detail")],es);let ts=class extends ne{constructor(){super(...arguments),this.sourceId="",this.sourceName="",this._name="",this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this._name=`${this.sourceName} (Copy)`}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _duplicate(){const e=this._name.trim();if(e){this._busy=!0,this._error=null;try{const t=await this.api.duplicateDevice(this.sourceId,e);this.dispatchEvent(new CustomEvent("device-duplicated",{detail:t,bubbles:!0,composed:!0})),this._close()}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error=$e("common.name_required")}_onKeyDown(e){"Enter"===e.key&&(e.preventDefault(),this._duplicate())}render(){return F`
            <ha-dialog
                open
                heading=${$e("dup.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?F`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <p class="hint">
                    ${$e("dup.hint_duplicating").split("{name}")[0]}<strong
                        >${this.sourceName}</strong
                    >${$e("dup.hint_duplicating").split("{name}")[1]??""}
                    ${$e("dup.hint_body")}
                </p>

                <div class="field">
                    <label>${$e("common.name")}</label>
                    <input
                        type="text"
                        .value=${this._name}
                        autofocus
                        required
                        @input=${e=>this._name=e.target.value}
                        @keydown=${this._onKeyDown}
                        @focus=${e=>e.target.select()}
                    />
                </div>

                <div class="dialog-actions">
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${$e("common.cancel")}
                    </button>
                    <button
                        class="action-btn create-btn"
                        @click=${this._duplicate}
                        ?disabled=${this._busy||!this._name.trim()}
                    >
                        ${this._busy?$e("dup.duplicating"):$e("dup.duplicate")}
                    </button>
                </div>
            </ha-dialog>
        `}};ts.styles=[Fi,a`
        .hint {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin: 8px 0 16px;
        }
        .field {
            display: block;
            margin: 12px 0;
            width: 100%;
        }
        .field label {
            display: block;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin-bottom: 4px;
        }
        .field input {
            width: 100%;
            padding: 8px 10px;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.95rem;
            font-family: inherit;
            box-sizing: border-box;
        }
        .field input:focus {
            outline: none;
            border-color: var(--primary-color);
        }
        /* Slimmer actions row than the shared one; ships this way. */
        .dialog-actions {
            margin-top: 16px;
            padding-top: 0;
            border-top: none;
        }
        /* Opacity in the transition so the Create hover fades, not snaps. */
        .action-btn {
            transition: background 150ms ease, opacity 150ms ease;
        }
        /* Brighter cancel than the shared secondary; ships this way. */
        .cancel-btn {
            color: var(--primary-text-color);
        }
        .create-btn {
            background: #2e7d32;
            color: #fff;
            border-color: #2e7d32;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `],e([pe({attribute:!1})],ts.prototype,"api",void 0),e([pe({attribute:!1})],ts.prototype,"sourceId",void 0),e([pe({attribute:!1})],ts.prototype,"sourceName",void 0),e([he()],ts.prototype,"_name",void 0),e([he()],ts.prototype,"_busy",void 0),e([he()],ts.prototype,"_error",void 0),ts=e([me("ir-duplicate-device-dialog")],ts);const is={media_player:"M21,17H3V5H21M21,3H3A2,2 0 0,0 1,5V17A2,2 0 0,0 3,19H8V21H16V19H21A2,2 0 0,0 23,17V5A2,2 0 0,0 21,3Z",ac:"M11,21H13V11.85L14.6,13.5L16,12.05L12,8L8,12.05L9.4,13.5L11,11.85V21M2,3V11C2,12.66 5.69,14 12,14C18.31,14 22,12.66 22,11V3H2M4,5H20V8.5C18.5,9.27 15.6,10 12,10C8.4,10 5.5,9.27 4,8.5V5Z",fan:"M12,11A1,1 0 0,0 11,12A1,1 0 0,0 12,13A1,1 0 0,0 13,12A1,1 0 0,0 12,11M12.5,2C17,2 17.11,5.57 14.75,6.75C13.76,7.24 13.32,8.29 13.13,9.22C13.61,9.42 14.03,9.73 14.35,10.13C18.05,8.13 22.03,8.92 22.03,12.5C22.03,17 18.46,17.1 17.28,14.73C16.78,13.74 15.72,13.3 14.79,13.11C14.59,13.59 14.28,14 13.88,14.34C15.87,18.03 15.08,22 11.5,22C7,22 6.91,18.42 9.27,17.24C10.25,16.75 10.69,15.71 10.89,14.79C10.4,14.59 9.97,14.27 9.65,13.87C5.96,15.85 2,15.07 2,11.5C2,7 5.56,6.89 6.74,9.26C7.24,10.25 8.29,10.68 9.22,10.87C9.41,10.39 9.73,9.97 10.14,9.65C8.15,5.95 8.94,2 12.5,2Z",light:"M12,2A7,7 0 0,0 5,9C5,11.38 6.19,13.47 8,14.74V17A1,1 0 0,0 9,18H15A1,1 0 0,0 16,17V14.74C17.81,13.47 19,11.38 19,9A7,7 0 0,0 12,2M9,21A1,1 0 0,0 10,22H14A1,1 0 0,0 15,21V20H9V21Z",switch:"M13,3H11V13H13V3M17.83,5.17L16.41,6.59C18,7.35 19,9.05 19,11A7,7 0 0,1 12,18A7,7 0 0,1 5,11C5,9.05 6,7.35 7.58,6.59L6.17,5.17C4.23,6.82 3,9.26 3,12A9,9 0 0,0 12,21A9,9 0 0,0 21,12C21,9.26 19.77,6.82 17.83,5.17Z",screen:"M20,19H4A2,2 0 0,1 2,17V7A2,2 0 0,1 4,5H20A2,2 0 0,1 22,7V17A2,2 0 0,1 20,19M4,7V17H20V7H4M12,10L16,14H13V17H11V14H8L12,10Z",other:"M11,2A2,2 0 0,0 9,4V8H4A2,2 0 0,0 2,10V13A2,2 0 0,0 4,15H5V21A2,2 0 0,0 7,23H17A2,2 0 0,0 19,21V15H20A2,2 0 0,0 22,13V10A2,2 0 0,0 20,8H15V4A2,2 0 0,0 13,2H11Z"},ss={media_player:"device_type.media_player",ac:"device_type.ac",fan:"device_type.fan",light:"device_type.light",switch:"device_type.switch",screen:"device_type.screen",other:"device_type.other_card"},rs="M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19M8,9H16V19H8V9M15.5,4L14.5,3H9.5L8.5,4H5V6H19V4H15.5Z";let os=class extends ne{constructor(){super(...arguments),this.devices=[],this.loading=!1,this.expandedDeviceId=null,this._emitters=[],this._captureProviders=[],this._pluckBlasters=[],this._expandedDevice=null,this._triggers=[],this._glowTriggerIds=new Set,this._editTrigger=null,this._confirmDeleteTrigger=null,this._duplicateTarget=null,this._confirmDeleteDevice=null,this._devicesVersion=0,this._localDevices=null,this._devicesSortable=null,this._pendingDevicesSave=null,this._unsubTriggerFired=null}connectedCallback(){super.connectedCallback(),this._discoverHardware(),this._loadTriggers(),this._subscribeTriggerFired()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeTriggerFired(),this._devicesSortable?.destroy(),this._devicesSortable=null,null!==this._pendingDevicesSave&&clearTimeout(this._pendingDevicesSave)}willUpdate(e){e.has("devices")&&(this._localDevices=null)}updated(e){(e.has("hass")||e.has("api"))&&this._discoverHardware(),e.has("api")&&this.api&&!this._unsubTriggerFired&&(this._loadTriggers(),this._subscribeTriggerFired()),e.has("expandedDeviceId")&&this._loadExpandedDevice(),this._syncDevicesSortable()}_syncDevicesSortable(){const e=this.renderRoot.querySelector(".device-grid");e&&!this._devicesSortable?this._attachDevicesSortable(e):!e&&this._devicesSortable&&(this._devicesSortable.destroy(),this._devicesSortable=null)}_attachDevicesSortable(e){this._devicesSortable=bi.create(e,{draggable:".device-card",filter:".card-action",preventOnFilter:!1,delay:150,delayOnTouchOnly:!0,animation:150,ghostClass:"sortable-ghost",onEnd:()=>{const t=Array.from(e.querySelectorAll(".device-card")).map(e=>e.dataset.id).filter(e=>!!e),i=this._localDevices??this.devices,s=new Map(i.map(e=>[e.id,e])),r=t.map(e=>s.get(e)).filter(e=>!!e);if(r.length===i.length){this._localDevices=r,this._devicesSortable?.destroy(),this._devicesSortable=null;for(const t of Array.from(e.querySelectorAll(".device-card, .expanded-detail")))t.remove();this._devicesVersion++,this._scheduleDevicesSave(r.map(e=>e.id))}}})}_scheduleDevicesSave(e){null!==this._pendingDevicesSave&&clearTimeout(this._pendingDevicesSave),this._pendingDevicesSave=window.setTimeout(async()=>{if(this._pendingDevicesSave=null,this.api)try{await this.api.reorderDevices(e)}catch{this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}},500)}async _loadExpandedDevice(){if(this.expandedDeviceId&&this.api)try{this._expandedDevice=await this.api.getDevice(this.expandedDeviceId)}catch{this._expandedDevice=null}else this._expandedDevice=null}async _onExpandedDeviceChanged(){await this._loadExpandedDevice(),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}_onExpandedDeviceDeleted(){this.dispatchEvent(new CustomEvent("device-deleted",{bubbles:!0,composed:!0}))}_onCommandsReordered(e){if(!this._expandedDevice)return;const t=e.detail?.commands;Array.isArray(t)&&(this._expandedDevice={...this._expandedDevice,commands:t})}_onCollapse(){this.dispatchEvent(new CustomEvent("device-selected",{detail:this.expandedDeviceId,bubbles:!0,composed:!0}))}async _discoverHardware(){const e=new Set;if(this.api)try{const t=await this.api.listReceivers();for(const i of t)e.add(i.entity_id)}catch{}const t=this.hass?.states??{},i=[];for(const[s,r]of Object.entries(t))!s.startsWith("infrared.")||e.has(s)||r.attributes.hair_observer||i.push({entity_id:s,name:r.attributes.friendly_name??s});if(this._emitters=i,this.api)try{this._captureProviders=await this.api.listCaptureProviders()}catch{}if(this.api)try{const{vendors:e}=await this.api.listPluckVendors(),t=[];for(const i of e)for(const e of i.blasters)t.push({integration:i.integration,entity_id:e.entity_id,name:e.name,vendorName:i.name});this._pluckBlasters=t}catch{this._pluckBlasters=[]}}_select(e){this.dispatchEvent(new CustomEvent("device-selected",{detail:e,bubbles:!0,composed:!0}))}_add(){this.dispatchEvent(new CustomEvent("add-device",{bubbles:!0,composed:!0}))}_openInPlucker(e){this.dispatchEvent(new CustomEvent("navigate-plucker",{detail:{vendor_entity_id:e},bubbles:!0,composed:!0}))}_openDuplicateDialog(e,t){t.stopPropagation(),this._duplicateTarget=e}_closeDuplicateDialog(){this._duplicateTarget=null}_onDeviceDuplicated(){this._duplicateTarget=null,this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}_requestDeleteDevice(e,t){t.stopPropagation(),this._confirmDeleteDevice=e}async _doDeleteDevice(){if(!this._confirmDeleteDevice||!this.api)return;const e=this._confirmDeleteDevice;this._confirmDeleteDevice=null;try{await this.api.deleteDevice(e.id),this.dispatchEvent(new CustomEvent("device-deleted",{bubbles:!0,composed:!0}))}catch{}}_navigateIntegration(e){const t=`/config/integrations/integration/${e}`;window.history.pushState(null,"",t),window.dispatchEvent(new PopStateEvent("popstate"))}async _loadTriggers(){if(this.api)try{this._triggers=await this.api.listTriggers()}catch{}}async _subscribeTriggerFired(){if(this.api)try{this._unsubTriggerFired=await this.api.subscribeTriggerFired(e=>{this._glowTriggerIds=new Set([...this._glowTriggerIds,e.trigger_id]),setTimeout(()=>{const t=new Set(this._glowTriggerIds);t.delete(e.trigger_id),this._glowTriggerIds=t},2500)})}catch{}}async _unsubscribeTriggerFired(){this._unsubTriggerFired&&(await this._unsubTriggerFired(),this._unsubTriggerFired=null)}_openEditTrigger(e,t){t.stopPropagation(),this._editTrigger=e}_closeEditTrigger(){this._editTrigger=null}async _onTriggerUpdated(){this._editTrigger=null,await this._loadTriggers()}async _toggleTriggerEnabled(e,t){t.stopPropagation();try{await this.api.updateTrigger(e.id,{enabled:!e.enabled}),await this._loadTriggers()}catch{}}_requestDeleteTrigger(e,t){t.stopPropagation(),this._confirmDeleteTrigger=e}async _doDeleteTrigger(){if(!this._confirmDeleteTrigger)return;const e=this._confirmDeleteTrigger;this._confirmDeleteTrigger=null;try{await this.api.deleteTrigger(e.id),await this._loadTriggers()}catch{}}_emitterIntegrationDomain(e){const t=this.hass?.entities?.[e];return t?.platform?t.platform:e.split(".")[0]}_getEmitterDeviceIds(){const e=new Set;for(const t of this._emitters){const i=this.hass?.entities?.[t.entity_id];i?.device_id&&e.add(i.device_id)}return e}_getEmitterEntityIdsByDevice(){const e=new Map;for(const t of this._emitters){const i=this.hass?.entities?.[t.entity_id],s=i?.device_id;if(!s)continue;const r=e.get(s)??[];r.push(t.entity_id),e.set(s,r)}return e}_isPre2026_6(){const e=this.hass?.config?.version;if(!e)return!1;const t=e.match(/^(\d+)\.(\d+)/);if(!t)return!1;const i=parseInt(t[1],10),s=parseInt(t[2],10);return i<2026||2026===i&&s<6}_resolveNavType(e,t){if("native"===e.type&&t){const e=this.hass?.entities?.[t]?.platform;return e||"esphome"}return e.type}_classifyHardware(){const e=this._getEmitterEntityIdsByDevice(),t=new Set(e.keys()),i=new Map;for(const s of this._captureProviders){let r,o;if("native"===s.type?(o=s.receiver_entity_id??s.device_id,r=this.hass?.entities?.[o]?.device_id,r||(r=o)):r=s.device_id,!r)continue;const a=i.get(r)??{device_id:r,name:s.name,nav_type:this._resolveNavType(s,o),has_native:!1,has_bridge:!1,has_tx:t.has(r),tx_entity_ids:e.get(r)??[]};"native"===s.type?(a.has_native=!0,a.native_entity_id=o):(a.has_bridge=!0,a.name=s.name,a.nav_type=s.type),i.set(r,a)}const s=Array.from(i.values()),r=s.filter(e=>e.has_tx);return{receivers:s,proxies:r}}_renderRxBadges(e){const t=!e.has_native&&e.has_bridge&&this._isPre2026_6();return F`
            ${e.has_native?F`<span
                      class="badge rx-native"
                      title=${$e("devlist.rx_native_title")}
                  >RX-NATIVE</span>`:B}
            ${e.has_bridge?F`<span
                      class="badge rx-bridge"
                      title=${e.has_native?$e("devlist.rx_bridge_active"):$e("devlist.rx_bridge_title")}
                  >RX-BRIDGE</span>`:B}
            ${t?F`<span
                      class="badge rx-native-disabled"
                      title=${$e("devlist.rx_upgrade_title")}
                  >RX-NATIVE</span>`:B}
        `}render(){if(this.loading)return F`<div class="loading">${$e("devlist.loading")}</div>`;const e=this._localDevices??this.devices,t=e.length>0,i=this._emitters.length>0,{receivers:s,proxies:r}=this._classifyHardware(),o=s.length>0,a=r.length>0,n=this._triggers.length>0;return t||i||o||a?F`
            <!-- Devices -->
            <div class="toolbar">
                <span class="toolbar-title">
                    <ha-svg-icon .path=${"M17.655 0C17.391 0.034 17.201 0.276 17.235 0.54C17.269 0.804 17.511 0.994 17.775 0.96C17.775 0.96 18.154 0.941 18.81 1.155C19.466 1.369 20.353 1.804 21.255 2.73C22.162 3.66 22.611 4.551 22.83 5.205C23.049 5.859 23.04 6.24 23.04 6.24C23.038 6.412 23.128 6.574 23.278 6.662C23.428 6.748 23.612 6.748 23.762 6.662C23.912 6.574 24.002 6.412 24 6.24C24 6.24 23.991 5.679 23.73 4.905C23.469 4.131 22.957 3.109 21.945 2.07C20.927 1.027 19.894 0.495 19.11 0.24C18.326 -0.015 17.745 0 17.745 0C17.73 0 17.715 0 17.7 0C17.685 0 17.67 0 17.655 0 Z M 13.77 2.88C13.26 2.88 12.746 3.064 12.345 3.435C12.339 3.441 12.336 3.444 12.33 3.45L0.57 15.255C-0.195 16.02 -0.188 17.286 0.555 18.09C0.561 18.096 0.564 18.099 0.57 18.105L5.955 23.475C6.72 24.24 7.971 24.232 8.775 23.49C8.781 23.484 8.784 23.481 8.79 23.475L20.55 11.715C20.556 11.706 20.561 11.694 20.565 11.685C21.289 10.841 21.315 9.6 20.55 8.835L15.165 3.45C14.782 3.067 14.28 2.88 13.77 2.88 Z M 17.67 2.88C17.406 2.904 17.211 3.141 17.235 3.405C17.259 3.669 17.496 3.864 17.76 3.84C17.76 3.84 17.91 3.831 18.21 3.93C18.51 4.029 18.911 4.241 19.335 4.665C19.759 5.089 19.971 5.49 20.07 5.79C20.169 6.09 20.16 6.24 20.16 6.24C20.158 6.412 20.248 6.574 20.398 6.662C20.548 6.748 20.732 6.748 20.882 6.662C21.032 6.574 21.122 6.412 21.12 6.24C21.12 6.24 21.111 5.91 20.97 5.49C20.829 5.07 20.561 4.511 20.025 3.975C19.489 3.439 18.93 3.171 18.51 3.03C18.09 2.889 17.76 2.88 17.76 2.88C17.745 2.88 17.73 2.88 17.715 2.88C17.7 2.88 17.685 2.88 17.67 2.88 Z M 13.77 3.84C14.04 3.84 14.297 3.932 14.49 4.125L19.875 9.51C20.263 9.898 20.274 10.569 19.845 11.07L8.115 22.785C7.671 23.194 7.018 23.188 6.63 22.8L1.26 17.43C1.254 17.424 1.251 17.421 1.245 17.415C0.849 16.971 0.862 16.328 1.245 15.945L13.005 4.14C13.226 3.936 13.5 3.84 13.77 3.84 Z M 13.44 6.72C11.325 6.72 9.6 8.445 9.6 10.56C9.6 12.675 11.325 14.4 13.44 14.4C15.555 14.4 17.28 12.675 17.28 10.56C17.28 8.445 15.555 6.72 13.44 6.72 Z M 13.44 7.68C15.036 7.68 16.32 8.964 16.32 10.56C16.32 12.156 15.036 13.44 13.44 13.44C11.844 13.44 10.56 12.156 10.56 10.56C10.56 8.964 11.844 7.68 13.44 7.68 Z M 13.44 9.6C12.909 9.6 12.48 10.029 12.48 10.56C12.48 11.091 12.909 11.52 13.44 11.52C13.971 11.52 14.4 11.091 14.4 10.56C14.4 10.029 13.971 9.6 13.44 9.6 Z M 7.2 12.96C6.669 12.96 6.24 13.389 6.24 13.92C6.24 14.451 6.669 14.88 7.2 14.88C7.731 14.88 8.16 14.451 8.16 13.92C8.16 13.389 7.731 12.96 7.2 12.96 Z M 4.8 15.36C4.269 15.36 3.84 15.789 3.84 16.32C3.84 16.851 4.269 17.28 4.8 17.28C5.331 17.28 5.76 16.851 5.76 16.32C5.76 15.789 5.331 15.36 4.8 15.36 Z M 10.08 15.84C9.549 15.84 9.12 16.269 9.12 16.8C9.12 17.331 9.549 17.76 10.08 17.76C10.611 17.76 11.04 17.331 11.04 16.8C11.04 16.269 10.611 15.84 10.08 15.84 Z M 7.68 18.24C7.149 18.24 6.72 18.669 6.72 19.2C6.72 19.731 7.149 20.16 7.68 20.16C8.211 20.16 8.64 19.731 8.64 19.2C8.64 18.669 8.211 18.24 7.68 18.24Z"}></ha-svg-icon>
                    ${$e("devlist.title")}
                    <span class="toolbar-count">(${this.devices.length})</span>
                </span>
                <button class="add-btn" @click=${this._add}>
                    <ha-svg-icon
                        .path=${"M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z"}
                    ></ha-svg-icon>
                    ${$e("devlist.add_device")}
                </button>
            </div>
            ${t?F`
                      <div class="grid device-grid">
                          ${He(this._devicesVersion,Ne(e,e=>e.id,e=>F`
                                  <div
                                      class="card device-card ${e.id===this.expandedDeviceId?"expanded":""}"
                                      data-id=${e.id}
                                      tabindex="0"
                                      @click=${()=>this._select(e.id)}
                                      @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._select(e.id))}}
                                  >
                                      <button
                                          class="card-action duplicate-action"
                                          title=${$e("dup.heading")}
                                          @click=${t=>this._openDuplicateDialog(e,t)}
                                      >
                                          <ha-svg-icon .path=${"M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"}></ha-svg-icon>
                                      </button>
                                      <button
                                          class="card-action delete-action"
                                          title=${$e("devlist.delete_device")}
                                          @click=${t=>this._requestDeleteDevice(e,t)}
                                      >
                                          <ha-svg-icon .path=${rs}></ha-svg-icon>
                                      </button>
                                      <div class="card-header">
                                          <ha-svg-icon
                                              .path=${is[e.device_type]??is.other}
                                          ></ha-svg-icon>
                                          <div class="card-name">
                                              ${e.name}
                                          </div>
                                      </div>
                                      <div class="card-meta">
                                          ${[e.manufacturer,$e(ss[e.device_type])].filter(Boolean).join(" • ")}
                                      </div>
                                      <div class="card-footer">
                                          <span class="badge cmd-badge">
                                              ${$e("devlist.cmd_badge",{count:e.command_count})}
                                          </span>
                                          ${e.emitter_entity_ids.length>0?F`<span class="badge tx-badge">${$e("devlist.tx_badge",{count:e.emitter_entity_ids.length})}</span>`:F`<span class="badge no-tx-badge">${$e("devlist.no_tx")}</span>`}
                                      </div>
                                  </div>
                                  ${e.id===this.expandedDeviceId&&this._expandedDevice?F`
                                            <div class="expanded-detail">
                                                <ir-device-detail
                                                    .api=${this.api}
                                                    .device=${this._expandedDevice}
                                                    .hass=${this.hass}
                                                    @device-changed=${this._onExpandedDeviceChanged}
                                                    @device-deleted=${this._onExpandedDeviceDeleted}
                                                    @commands-reordered=${this._onCommandsReordered}
                                                    @trigger-changed=${this._loadTriggers}
                                                    @collapse=${this._onCollapse}
                                                ></ir-device-detail>
                                            </div>
                                        `:B}
                              `))}
                      </div>
                  `:F`
                      <div class="empty-devices">
                          No devices yet. Sniff some signals, then add your first device.
                      </div>
                  `}

            <!-- Triggers -->
            ${n?F`
                      <div class="section-header">
                          <h2>${$e("popover.triggers")}</h2>
                          <span class="section-count">${this._triggers.length}</span>
                      </div>
                      <div class="grid">
                          ${this._triggers.map(e=>F`
                                  <div
                                      class="card trigger-card ${this._glowTriggerIds.has(e.id)?"trigger-glow":""} ${e.enabled?"":"trigger-disabled"}"
                                      tabindex="0"
                                      @click=${t=>this._openEditTrigger(e,t)}
                                      @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._openEditTrigger(e,t))}}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon class="trigger-icon" .path=${"M7,2V13H10V22L17,10H13L17,2H7Z"}></ha-svg-icon>
                                          <div class="card-name">${e.name}</div>
                                      </div>
                                      <div class="card-meta">${$e("trigger.event")}</div>
                                      <div class="card-footer">
                                          ${e.min_hits>1?F`<span class="badge trigger-hits-badge">
                                                    ${$e("devlist.hits_badge",{count:e.min_hits})}
                                                </span>`:B}
                                          <span
                                              class="badge trigger-toggle ${e.enabled?"trigger-enabled":"trigger-off"}"
                                              @click=${t=>this._toggleTriggerEnabled(e,t)}
                                          >${e.enabled?$e("devlist.on"):$e("devlist.off")}</span>
                                          <ha-svg-icon
                                              class="trigger-trash"
                                              .path=${rs}
                                              title=${$e("devlist.delete_trigger")}
                                              @click=${t=>this._requestDeleteTrigger(e,t)}
                                          ></ha-svg-icon>
                                      </div>
                                  </div>
                              `)}
                      </div>
                  `:B}

            <!-- Blasters (Pluckable) -- vendor IR blasters HAIR can pull from -->
            ${this._pluckBlasters.length>0?F`
                      <div class="section-header">
                          <h2>${$e("devlist.blasters")}</h2>
                          <span class="section-count"
                              >${this._pluckBlasters.length}</span
                          >
                      </div>
                      <div class="grid">
                          ${this._pluckBlasters.map(e=>F`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      title=${$e("devlist.open_plucker_title")}
                                      @click=${()=>this._openInPlucker(e.entity_id)}
                                      @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._openInPlucker(e.entity_id))}}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon .path=${"M0.861,24c-0.22,0-0.441-0.084-0.609-0.252c-0.336-0.336-0.336-0.882,0-1.218l1.563-1.563c1.648-1.649,3.474-4.166,5.588-7.082c2.984-4.116,6.367-8.781,10.695-13.109c0.081-0.081,0.178-0.145,0.284-0.189l1.283-0.523c0.441-0.18,0.943,0.032,1.123,0.472l-0.472,1.123L19.194,2.116c-4.175,4.199-7.478,8.755-10.397,12.78c-0.275,0.379-0.545,0.752-0.811,1.117c0.365-0.266,0.738-0.536,1.117-0.811C13.128,12.284,17.685,8.98,21.884,4.806l0.457-1.121L23.464,3.212c0.44,0.18,0.652,0.682,0.472,1.123l-0.523,1.283c-0.043,0.106-0.107,0.203-0.188,0.284c-4.329,4.329-8.994,7.711-13.109,10.695c-2.915,2.114-5.433,3.939-7.082,5.588l-1.563,1.563C1.302,23.916,1.082,24,0.861,24z"}></ha-svg-icon>
                                          <div class="card-name">
                                              ${e.vendorName}: ${e.name}
                                          </div>
                                      </div>
                                      <div class="card-meta">${e.entity_id}</div>
                                      <div class="card-footer">
                                          <span class="badge pluck-badge"
                                              >${$e("devlist.open_plucker")}</span
                                          >
                                      </div>
                                  </div>
                              `)}
                      </div>
                  `:B}

            <!-- Emitters -->
            ${i?F`
                      <div class="section-header">
                          <h2>${$e("devlist.emitters")}</h2>
                          <span class="section-count">${this._emitters.length}</span>
                      </div>
                      <div class="grid">
                          ${this._emitters.map(e=>F`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      @click=${()=>this._navigateIntegration(this._emitterIntegrationDomain(e.entity_id))}
                                      @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._navigateIntegration(this._emitterIntegrationDomain(e.entity_id)))}}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon .path=${"M9,10V16H15V10H19L12,3L5,10H9M12,5.8L14.2,8H13V14H11V8H9.8L12,5.8M19,18H5V20H19V18Z"}></ha-svg-icon>
                                          <div class="card-name">${e.name}</div>
                                      </div>
                                      <div class="card-meta">${e.entity_id}</div>
                                      <div class="card-footer">
                                          <span
                                              class="badge tx-native"
                                              title=${$e("devlist.tx_native_title")}
                                          >TX-NATIVE</span>
                                      </div>
                                  </div>
                              `)}
                      </div>
                  `:B}

            <!-- Receivers (capture-capable hardware; proxies appear here too by design) -->
            ${o?F`
                      <div class="section-header">
                          <h2>${$e("devlist.receivers")}</h2>
                          <span class="section-count">${s.length}</span>
                      </div>
                      <div class="grid">
                          ${s.map(e=>F`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      @click=${()=>this._navigateIntegration(e.nav_type)}
                                      @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._navigateIntegration(e.nav_type))}}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon .path=${"M13,5V11H14.17L12,13.17L9.83,11H11V5H13M15,3H9V9H5L12,16L19,9H15V3M19,18H5V20H19V18Z"}></ha-svg-icon>
                                          <div class="card-name">${e.name}</div>
                                      </div>
                                      <div class="card-meta">${e.native_entity_id??e.nav_type}</div>
                                      <div class="card-footer">
                                          ${this._renderRxBadges(e)}
                                      </div>
                                  </div>
                              `)}
                      </div>
                  `:B}

            <!-- Proxies (TX + RX hardware) -->
            ${a?F`
                      <div class="section-header">
                          <h2>${$e("devlist.proxies")}</h2>
                          <span class="section-count">${r.length}</span>
                      </div>
                      <div class="grid">
                          ${r.map(e=>F`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      @click=${()=>this._navigateIntegration(e.nav_type)}
                                      @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._navigateIntegration(e.nav_type))}}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon .path=${"M12,10A2,2 0 0,1 14,12C14,12.5 13.82,12.94 13.53,13.29L16.7,22H14.57L12,14.93L9.43,22H7.3L10.47,13.29C10.18,12.94 10,12.5 10,12A2,2 0 0,1 12,10M12,8A4,4 0 0,0 8,12C8,12.5 8.1,13 8.28,13.46L7.4,15.86C6.53,14.81 6,13.47 6,12A6,6 0 0,1 12,6A6,6 0 0,1 18,12C18,13.47 17.47,14.81 16.6,15.86L15.72,13.46C15.9,13 16,12.5 16,12A4,4 0 0,0 12,8M12,4A8,8 0 0,0 4,12C4,14.36 5,16.5 6.64,17.94L5.92,19.94C3.54,18.11 2,15.23 2,12A10,10 0 0,1 12,2A10,10 0 0,1 22,12C22,15.23 20.46,18.11 18.08,19.94L17.36,17.94C19,16.5 20,14.36 20,12A8,8 0 0,0 12,4Z"}></ha-svg-icon>
                                          <div class="card-name">${e.name}</div>
                                      </div>
                                      ${e.tx_entity_ids[0]?F`<div class="card-meta">${e.tx_entity_ids[0]}</div>`:B}
                                      <div class="card-meta">${e.native_entity_id??e.nav_type}</div>
                                      <div class="card-footer">
                                          <span
                                              class="badge tx-native"
                                              title=${$e("devlist.tx_native_title")}
                                          >TX-NATIVE</span>
                                          ${this._renderRxBadges(e)}
                                      </div>
                                  </div>
                              `)}
                      </div>
                  `:B}

            ${this._editTrigger?F`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .trigger=${this._editTrigger}
                          @trigger-saved=${this._onTriggerUpdated}
                          @closed=${this._closeEditTrigger}
                      ></ir-trigger-dialog>
                  `:B}

            ${this._confirmDeleteTrigger?F`
                      <ir-confirm-dialog
                          title=${$e("mirror.del_trigger_title")}
                          message=${$e("devlist.del_trigger_msg",{name:this._confirmDeleteTrigger.name})}
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._doDeleteTrigger}
                          @closed=${()=>this._confirmDeleteTrigger=null}
                      ></ir-confirm-dialog>
                  `:B}

            ${this._duplicateTarget&&this.api?F`
                      <ir-duplicate-device-dialog
                          .api=${this.api}
                          .sourceId=${this._duplicateTarget.id}
                          .sourceName=${this._duplicateTarget.name}
                          @device-duplicated=${this._onDeviceDuplicated}
                          @closed=${this._closeDuplicateDialog}
                      ></ir-duplicate-device-dialog>
                  `:B}

            ${this._confirmDeleteDevice?F`
                      <ir-confirm-dialog
                          title=${$e("devlist.del_device_title")}
                          message=${$e("devlist.del_device_msg",{name:this._confirmDeleteDevice.name})}
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._doDeleteDevice}
                          @closed=${()=>this._confirmDeleteDevice=null}
                      ></ir-confirm-dialog>
                  `:B}
        `:F`
                <ha-card class="empty">
                    <h2>${$e("devlist.empty_title")}</h2>
                    <p>${$e("devlist.empty_sub")}</p>
                    <mwc-button raised @click=${this._add}>${$e("devlist.add_device_plus")}</mwc-button>
                </ha-card>
            `}};os.styles=a`
        :host {
            display: block;
        }
        .loading,
        .empty {
            padding: 24px;
            text-align: center;
            color: var(--secondary-text-color);
        }
        .empty h2 {
            margin-top: 8px;
            color: var(--primary-text-color);
        }

        .empty-devices {
            text-align: center;
            padding: 24px 16px;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
            margin-bottom: 16px;
        }

        /* --- Devices toolbar (matches sniffer) --- */
        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .toolbar-title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--primary-text-color);
        }
        .toolbar-title ha-svg-icon {
            --mdc-icon-size: 24px;
            color: var(--primary-color);
        }
        .add-btn {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            background: none;
            color: var(--primary-color);
            border: 1px solid var(--primary-color);
            border-radius: 4px;
            padding: 4px 12px;
            font-size: 0.85rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            transition: background 150ms ease;
        }
        .add-btn ha-svg-icon {
            --mdc-icon-size: 18px;
        }
        .add-btn:hover {
            background: rgba(var(--rgb-primary-color, 33, 150, 243), 0.08);
        }
        .toolbar-count {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
        }

        /* --- Section headers (neutral) --- */
        .section-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 24px 0 10px;
            padding-bottom: 6px;
            border-bottom: 2px solid var(--divider-color);
        }
        .section-header:first-child {
            margin-top: 0;
        }
        .section-header h2 {
            margin: 0;
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
            color: var(--secondary-text-color);
        }
        .section-count {
            font-size: 0.75rem;
            font-weight: 600;
            padding: 1px 7px;
            border-radius: 4px;
            background: var(--secondary-background-color);
            color: var(--secondary-text-color);
        }

        /* --- Card grid (compact) --- */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 12px;
        }

        /* --- Shared card styles (neutral, sniffer palette) --- */
        .card {
            padding: 12px;
            cursor: pointer;
            border-radius: 8px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            transition: transform 120ms ease, box-shadow 120ms ease;
        }
        .card:hover,
        .card:focus-visible {
            background: var(--secondary-background-color);
            outline: none;
        }
        .card-header {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .card-header ha-svg-icon {
            --mdc-icon-size: 24px;
            color: var(--secondary-text-color);
            /* Long card names (eg the Athom proxy transmitter title) can
               otherwise squeeze the flex item below its intrinsic size. */
            flex-shrink: 0;
        }
        .card-name {
            font-size: 0.95rem;
            font-weight: 500;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .card-meta {
            margin-top: 6px;
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .card-footer {
            margin-top: 8px;
            display: flex;
            gap: 6px;
            align-items: center;
        }
        .badge {
            border-radius: 4px;
            padding: 2px 8px;
            font-size: 0.72rem;
            font-weight: 500;
        }

        /* Command count badge (green) */
        .cmd-badge {
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
        }

        /* TX badge (amber text, dark bg) */
        .tx-badge {
            background: var(--secondary-background-color);
            color: #ff9800;
        }

        /* RX badge (blue text, dark bg) */
        .rx-badge {
            background: var(--secondary-background-color);
            color: var(--primary-color, #2196f3);
        }

        /* No TX warning (muted) */
        .no-tx-badge {
            background: var(--secondary-background-color);
            color: var(--disabled-text-color, #999);
            font-style: italic;
        }

        /* Hardware section badges -- consistent <direction>-<source> pattern. */
        /* TX-NATIVE and RX-NATIVE share the green palette of .cmd-badge. */
        .tx-native,
        .rx-native {
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
        }
        /* RX-BRIDGE uses HAIR's existing orange. */
        .rx-bridge {
            background: rgba(255, 152, 0, 0.15);
            color: #ff9800;
        }
        /* Pre-2026.6 upgrade hint: grayed RX-NATIVE alongside RX-BRIDGE. */
        .rx-native-disabled {
            background: var(--secondary-background-color);
            color: var(--disabled-text-color, #999);
            opacity: 0.6;
            cursor: help;
        }

        /* --- Expanded detail row --- */
        .expanded-detail {
            grid-column: 1 / -1;
            background: var(--card-background-color);
            border: 1px solid var(--divider-color);
            border-radius: 8px;
            padding: 16px;
            animation: expand-in 200ms ease;
        }
        @keyframes expand-in {
            from { opacity: 0; transform: translateY(-8px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* --- Device card expanded highlight --- */
        .device-card {
            position: relative;
        }
        .device-card.expanded {
            border-color: #2e7d32;
            box-shadow: 0 0 0 1px #2e7d32;
        }
        /* SortableJS marks the card being dragged. */
        .device-card.sortable-ghost {
            opacity: 0.4;
        }
        .device-card.sortable-chosen {
            cursor: grabbing;
        }

        /* --- Card corner actions (duplicate top-right, delete bottom-right) --- */
        .card-action {
            position: absolute;
            background: transparent;
            border: none;
            padding: 4px;
            border-radius: 4px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: background 120ms ease, color 120ms ease, opacity 120ms ease;
        }
        .card-action ha-svg-icon {
            /* Default card-action glyph size. The duplicate-action overrides
               this with a smaller value because the copy MDI glyph fills more
               of its viewbox than the trash glyph. */
            --mdc-icon-size: 16px;
        }
        .duplicate-action {
            top: 6px;
            right: 6px;
            color: var(--disabled-text-color, #999);
            opacity: 0.55;
        }
        .duplicate-action ha-svg-icon {
            /* Copy MDI glyph fills more of its viewbox than the trash glyph,
               so render it smaller to land at the same visual size as the
               trash icon in the opposite corner. */
            --mdc-icon-size: 13px;
        }
        .duplicate-action:hover {
            color: var(--primary-text-color);
            opacity: 1;
        }
        .delete-action {
            bottom: 6px;
            right: 6px;
            color: var(--disabled-text-color, #999);
            opacity: 0.55;
        }
        .delete-action:hover {
            background: rgba(244, 67, 54, 0.12);
            color: #f44336;
            opacity: 1;
        }

        /* --- Hardware cards inherit shared .card styles --- */
        .hw-card {
            /* Neutral -- no per-section color backgrounds */
        }
        /* "Open in Plucker" badge -- standard badge form, no stroke. */
        .pluck-badge {
            background: var(--secondary-background-color);
            color: #78909c;
            text-transform: uppercase;
        }

        /* --- Trigger section --- */
        .trigger-card {
            transition: transform 120ms ease, box-shadow 300ms ease,
                        border-color 300ms ease, background 400ms ease;
        }
        .trigger-card .trigger-icon {
            transition: color 200ms ease, transform 200ms ease;
        }
        .trigger-card.trigger-disabled {
            opacity: 0.5;
        }

        /* --- Trigger fire animation (card + bolt) --- */
        .trigger-card.trigger-glow {
            border-color: #d4a017;
            background: rgba(212, 160, 23, 0.08);
            animation: trigger-card-flash 2.4s ease-out;
        }
        .trigger-card.trigger-glow .trigger-icon {
            color: #f5a623;
            animation: trigger-bolt-pulse 2.4s ease-out;
        }
        @keyframes trigger-card-flash {
            0% {
                background: rgba(212, 160, 23, 0.18);
                border-color: #f5a623;
                box-shadow: 0 0 16px 4px rgba(245, 166, 35, 0.4);
            }
            30% {
                background: rgba(212, 160, 23, 0.1);
                border-color: #d4a017;
                box-shadow: 0 0 8px 2px rgba(245, 166, 35, 0.2);
            }
            60% {
                background: rgba(212, 160, 23, 0.06);
                box-shadow: 0 0 4px 1px rgba(245, 166, 35, 0.1);
            }
            100% {
                background: transparent;
                border-color: var(--divider-color);
                box-shadow: none;
            }
        }
        @keyframes trigger-bolt-pulse {
            0% { color: #ffb300; transform: scale(1.4); }
            15% { color: #f5a623; transform: scale(1.0); }
            30% { color: #ffb300; transform: scale(1.35); }
            50% { color: #d4a017; transform: scale(1.0); }
            100% { color: var(--secondary-text-color); transform: scale(1.0); }
        }
        .trigger-hits-badge {
            background: rgba(184, 153, 48, 0.15);
            color: #b89930;
            text-transform: uppercase;
        }
        .trigger-toggle {
            cursor: pointer;
            transition: background 150ms ease;
        }
        .trigger-toggle.trigger-enabled {
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
        }
        .trigger-toggle.trigger-enabled:hover {
            background: rgba(46, 125, 50, 0.25);
        }
        .trigger-toggle.trigger-off {
            background: var(--secondary-background-color);
            color: var(--disabled-text-color, #999);
        }
        .trigger-toggle.trigger-off:hover {
            background: rgba(0, 0, 0, 0.1);
        }
        /* Matches the device-card .delete-action palette so the trigger
           trash and the device-card trash read as the same control. */
        .trigger-trash {
            --mdc-icon-size: 16px;
            color: var(--disabled-text-color, #999);
            cursor: pointer;
            margin-left: auto;
            opacity: 0.55;
            border-radius: 4px;
            padding: 2px;
            transition: background 150ms ease, color 150ms ease, opacity 150ms ease;
        }
        .trigger-trash:hover {
            background: rgba(244, 67, 54, 0.12);
            color: #f44336;
            opacity: 1;
        }
    `,e([pe({attribute:!1})],os.prototype,"devices",void 0),e([pe({attribute:!1})],os.prototype,"hass",void 0),e([pe({attribute:!1})],os.prototype,"api",void 0),e([pe({type:Boolean})],os.prototype,"loading",void 0),e([pe({attribute:!1})],os.prototype,"expandedDeviceId",void 0),e([he()],os.prototype,"_emitters",void 0),e([he()],os.prototype,"_captureProviders",void 0),e([he()],os.prototype,"_pluckBlasters",void 0),e([he()],os.prototype,"_expandedDevice",void 0),e([he()],os.prototype,"_triggers",void 0),e([he()],os.prototype,"_glowTriggerIds",void 0),e([he()],os.prototype,"_editTrigger",void 0),e([he()],os.prototype,"_confirmDeleteTrigger",void 0),e([he()],os.prototype,"_duplicateTarget",void 0),e([he()],os.prototype,"_confirmDeleteDevice",void 0),e([he()],os.prototype,"_devicesVersion",void 0),e([he()],os.prototype,"_localDevices",void 0),os=e([me("ir-device-list")],os);const as=[{value:"media_player",label:"Media Player"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"light",label:"Light"},{value:"switch",label:"Switch"},{value:"screen",label:"Screen / Shade"},{value:"other",label:"Other"}];let ns=class extends ne{constructor(){super(...arguments),this._name="",this._deviceType="media_player",this._emitterIds=[],this._captureProviders=[],this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this._loadCaptureProviders()}async _loadCaptureProviders(){try{this._captureProviders=await this.api.listCaptureProviders()}catch{}}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _create(){if(this._name.trim())if(0!==this._emitterIds.length){this._busy=!0,this._error=null;try{const e=this._captureProviders[0]??null,t=await this.api.createDevice({name:this._name.trim(),device_type:this._deviceType,emitter_entity_ids:this._emitterIds,capture_device_id:e?.device_id??null,capture_provider_type:e?.type??"esphome"});this.dispatchEvent(new CustomEvent("device-created",{detail:t,bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error=$e("adddev.emitter_required");else this._error=$e("common.name_required")}render(){return F`
            <ha-dialog
                open
                heading=${$e("adddev.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?F`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <div class="field">
                    <label>${$e("common.name")}</label>
                    <input
                        type="text"
                        .value=${this._name}
                        placeholder=${$e("common.device_name_placeholder")}
                        required
                        autofocus
                        @input=${e=>this._name=e.target.value}
                    />
                </div>

                <div class="field">
                    <label>${$e("common.device_type")}</label>
                    <select
                        .value=${this._deviceType}
                        @change=${e=>this._deviceType=e.target.value}
                    >
                        ${as.map(e=>F`
                                <option
                                    value=${e.value}
                                    ?selected=${this._deviceType===e.value}
                                >
                                    ${$e(`device_type.${e.value}`)}
                                </option>
                            `)}
                    </select>
                </div>

                <ir-emitter-picker
                    .hass=${this.hass}
                    .api=${this.api}
                    .value=${this._emitterIds}
                    ?disabled=${this._busy}
                    @emitters-changed=${e=>this._emitterIds=e.detail.value}
                ></ir-emitter-picker>

                <div class="dialog-actions">
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${$e("common.cancel")}
                    </button>
                    <button
                        class="action-btn create-btn"
                        @click=${this._create}
                        ?disabled=${this._busy}
                    >
                        ${this._busy?$e("common.creating"):$e("adddev.create")}
                    </button>
                </div>
            </ha-dialog>
        `}};ns.styles=[Fi,a`
        ha-alert {
            display: block;
            margin: 8px 0;
        }
        .create-btn {
            background: #2e7d32;
            color: #fff;
            border-color: #2e7d32;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `],e([pe({attribute:!1})],ns.prototype,"api",void 0),e([pe({attribute:!1})],ns.prototype,"hass",void 0),e([he()],ns.prototype,"_name",void 0),e([he()],ns.prototype,"_deviceType",void 0),e([he()],ns.prototype,"_emitterIds",void 0),e([he()],ns.prototype,"_captureProviders",void 0),e([he()],ns.prototype,"_busy",void 0),e([he()],ns.prototype,"_error",void 0),ns=e([me("ir-add-device-dialog")],ns);let ls=class extends ne{constructor(){super(...arguments),this.deviceId="",this.disabled=!1,this._editing=!1,this._draft=""}updated(e){if(e.has("_editing")&&this._editing){const e=this.shadowRoot?.querySelector(".alias-input");e?.focus(),e?.select()}}_startEdit(e){this.disabled||(e?.stopPropagation(),this._draft=this.signal.alias??"",this._editing=!0)}_onKeydown(e){"Enter"===e.key?this._commit():"Escape"===e.key&&(this._editing=!1)}async _commit(){if(!this._editing)return;const e=this._draft.trim();this._editing=!1,await this._save(e)}async _clear(){this._editing=!1,await this._save("")}async _save(e){try{await this.api.setSignalAlias(this.deviceId,this.signal.id,e),this.dispatchEvent(new CustomEvent("alias-changed",{detail:{id:this.signal.id,alias:e},bubbles:!0,composed:!0}))}catch(e){this.dispatchEvent(new CustomEvent("alias-error",{detail:e.message,bubbles:!0,composed:!0}))}}render(){const e=this.signal;return this._editing?F`
                <span class="alias-edit" @click=${e=>e.stopPropagation()}>
                    <input
                        class="alias-input"
                        type="text"
                        .value=${this._draft}
                        placeholder=${$e("alias.placeholder")}
                        @input=${e=>{this._draft=e.target.value}}
                        @keydown=${this._onKeydown}
                        @blur=${()=>{this._commit()}}
                    />
                    <button
                        class="alias-clear"
                        title=${$e("alias.clear")}
                        @mousedown=${e=>e.preventDefault()}
                        @click=${()=>{this._clear()}}
                    >✕</button>
                </span>
            `:e.alias?F`
                <span
                    class="alias-display ${this.disabled?"locked":""}"
                    title=${this.disabled?"":$e("alias.edit")}
                    @click=${e=>this._startEdit(e)}
                >
                    <span class="alias-label">alias</span>
                    <span class="alias-name">${e.alias}</span>
                </span>
            `:F`
            <span
                class="diamonds-wrap ${this.disabled?"locked":""}"
                title=${this.disabled?"":$e("alias.name")}
                @click=${e=>this._startEdit(e)}
            >
                ${e.sl_pattern?F`<span class="diamonds"
                          >${[...e.sl_pattern].map(e=>"L"===e?F`<span class="diamond long">◆</span>`:F`<span class="diamond short">◇</span>`)}</span
                      >`:F`<span class="signal-short-label">IR Signal</span>`}
                <ha-svg-icon class="alias-pencil" .path=${"M14.06,9L15,9.94L5.92,19H5V18.08L14.06,9M17.66,3C17.41,3 17.15,3.1 16.96,3.29L15.13,5.12L18.88,8.87L20.71,7.04C21.1,6.65 21.1,6.02 20.71,5.63L18.37,3.29C18.17,3.09 17.92,3 17.66,3M14.06,6.19L3,17.25V21H6.75L17.81,9.94L14.06,6.19Z"}></ha-svg-icon>
            </span>
        `}};ls.styles=a`
        :host {
            display: inline-flex;
            align-items: center;
            min-width: 0;
        }
        .diamonds-wrap {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            cursor: pointer;
        }
        .diamonds-wrap.locked,
        .alias-display.locked {
            cursor: default;
        }
        .diamonds-wrap.locked .alias-pencil {
            display: none;
        }
        .diamonds {
            display: inline-flex;
            gap: 1px;
            flex-wrap: wrap;
            line-height: 1;
        }
        .diamond {
            font-size: 0.7rem;
        }
        .diamond.long {
            color: var(--primary-color);
        }
        .diamond.short {
            color: var(--warning-color, #ff9800);
        }
        .signal-short-label {
            font-size: 0.82rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
        .alias-pencil {
            --mdc-icon-size: 13px;
            color: var(--secondary-text-color);
            opacity: 0;
            transition: opacity 150ms ease;
        }
        .diamonds-wrap:hover .alias-pencil {
            opacity: 0.7;
        }
        .alias-display {
            display: inline-flex;
            align-items: baseline;
            gap: 7px;
            cursor: pointer;
        }
        .alias-label {
            font-size: 0.6rem;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            color: #ba7517;
        }
        .alias-name {
            font-size: 0.9rem;
            color: var(--primary-color);
        }
        .alias-edit {
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .alias-input {
            font-size: 0.85rem;
            font-family: inherit;
            border: 1px solid #b87333;
            border-radius: 4px;
            padding: 2px 6px;
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color);
            outline: none;
            width: 150px;
        }
        .alias-clear {
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            background: none;
            color: var(--secondary-text-color);
            cursor: pointer;
            font-size: 0.8rem;
            line-height: 1;
            padding: 3px 6px;
            transition: color 150ms ease, border-color 150ms ease;
        }
        .alias-clear:hover {
            color: #e65100;
            border-color: rgba(230, 81, 0, 0.4);
        }
    `,e([pe({attribute:!1})],ls.prototype,"api",void 0),e([pe()],ls.prototype,"deviceId",void 0),e([pe({attribute:!1})],ls.prototype,"signal",void 0),e([pe({type:Boolean})],ls.prototype,"disabled",void 0),e([he()],ls.prototype,"_editing",void 0),e([he()],ls.prototype,"_draft",void 0),ls=e([me("ir-signal-alias")],ls);const ds=[{value:"media_player",label:"Media Player"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"light",label:"Light"},{value:"switch",label:"Switch"},{value:"screen",label:"Screen / Shade"},{value:"other",label:"Other"}];let cs=class extends ne{constructor(){super(...arguments),this.suggestedDeviceName="",this.initialMode="existing",this._mode="existing",this._devices=[],this._selectedDeviceId="",this._commandName="",this._newName="",this._newType="media_player",this._newEmitterIds=[],this._templates=[],this._customCommand=!1,this._sendCount=1,this._dittoCount=1,this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this._mode=this.initialMode,this.suggestedDeviceName&&!this._newName&&(this._newName=this.suggestedDeviceName),this._sendCount=this.signal?.send_count??1,this._dittoCount=this.signal?.repeat_count??1,this._loadDevices(),"new"===this._mode&&this._loadTemplates(this._newType)}async _loadDevices(){try{if(this._devices=await this.api.listDevices(),this.suggestedDeviceName&&!this._selectedDeviceId){const e=this.suggestedDeviceName.toLowerCase(),t=this._devices.find(t=>t.name.toLowerCase()===e);if(t)return this._selectedDeviceId=t.id,void this._loadTemplates(t.device_type)}if("existing"===this._mode&&this._devices.length>0){const e=this._devices[0];this._loadTemplates(e.device_type)}else"existing"===this._mode&&this._loadTemplates("other")}catch{"existing"===this._mode&&this._loadTemplates("other")}}async _loadTemplates(e){try{this._templates=await this.api.listTemplates(e)}catch{this._templates=[]}this._customCommand||(this._commandName="")}_activeDeviceType(){if("new"===this._mode)return this._newType;const e=this._devices.find(e=>e.id===this._selectedDeviceId);return e?.device_type??"other"}_onDeviceSelected(e){this._selectedDeviceId=e.target.value;const t=this._devices.find(e=>e.id===this._selectedDeviceId);t&&this._loadTemplates(t.device_type)}_onNewTypeChanged(e){this._newType=e.target.value,this._loadTemplates(this._newType)}_switchMode(e){e!==this._mode&&(this._mode=e,this._customCommand=!1,this._commandName="",this._loadTemplates(this._activeDeviceType()))}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_onSendCountInput(e){const t=parseInt(e.target.value,10);this._sendCount=Number.isNaN(t)?1:Math.max(1,Math.min(t,10))}_onDittoInput(e){const t=parseInt(e.target.value,10);this._dittoCount=Number.isNaN(t)?0:Math.max(0,Math.min(t,20))}async _assign(){const e=this._commandName.trim();if(e){this._busy=!0,this._error=null;try{let t;if("existing"===this._mode){if(!this._selectedDeviceId)return this._error=$e("assign.target_required"),void(this._busy=!1);t=await this.api.assignSignal({device_id:this.unknownDeviceId,signal_id:this.signal.id,hair_device_id:this._selectedDeviceId,command_name:e,send_count:this._sendCount,repeat_count:this.signal.decoded_fingerprint?this._dittoCount:void 0})}else{if(!this._newName.trim())return this._error=$e("promote.device_name_required"),void(this._busy=!1);if(0===this._newEmitterIds.length)return this._error=$e("promote.emitter_required"),void(this._busy=!1);t=await this.api.assignToNewDevice({device_id:this.unknownDeviceId,signal_id:this.signal.id,device_name:this._newName.trim(),device_type:this._newType,emitter_entity_ids:this._newEmitterIds,command_name:e,send_count:this._sendCount,repeat_count:this.signal.decoded_fingerprint?this._dittoCount:void 0})}t.assigned?this.dispatchEvent(new CustomEvent("signal-assigned",{detail:t,bubbles:!0,composed:!0})):this._error=$e("assign.failed_duplicate")}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error=$e("assign.command_required")}_fmtTime(e){try{return new Date(e).toLocaleString(xe(),{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return e}}render(){const e=this.signal.frequency?`${Math.round(this.signal.frequency/1e3)}kHz`:"";return F`
            <ha-dialog
                open
                heading=${$e("assign.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?F`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <div class="signal-header">
                    ${this.suggestedDeviceName?F`<div class="device-name">${this.suggestedDeviceName}</div>`:""}
                    <div class="signal-detail">
                        <ir-signal-alias
                            .api=${this.api}
                            .deviceId=${this.unknownDeviceId}
                            .signal=${this.signal}
                            disabled
                        ></ir-signal-alias>
                    </div>
                    <div class="signal-stats">
                        <span>${$e("assign.hits",{count:this.signal.hit_count})}</span>
                        ${e?F`<span>${e}</span>`:""}
                        <span>${this._fmtTime(this.signal.last_seen)}</span>
                    </div>
                </div>

                <!-- Mode tabs -->
                <div class="mode-tabs">
                    <button
                        class="mode-tab ${"existing"===this._mode?"active":""}"
                        @click=${()=>{this._switchMode("existing")}}
                    >
                        ${$e("assign.mode_existing")}
                    </button>
                    <button
                        class="mode-tab ${"new"===this._mode?"active":""}"
                        @click=${()=>{this._switchMode("new")}}
                    >
                        ${$e("assign.mode_new")}
                    </button>
                </div>

                ${"existing"===this._mode?this._renderExistingMode():this._renderNewMode()}

                <!-- Command name (shared by both modes) -->
                ${this._renderCommandPicker()}

                <!-- Whole-frame send count (shared by both modes) -->
                <div class="field">
                    <label>${$e("assign.send_times")}</label>
                    <input
                        class="send-count"
                        type="number"
                        min="1"
                        max="10"
                        .value=${String(this._sendCount)}
                        @input=${this._onSendCountInput}
                    />
                    <div class="hint">
                        ${$e("assign.send_times_hint")}
                    </div>
                </div>

                ${this.signal.decoded_fingerprint?F`<!-- NEC ditto count (decoded signals only) -->
                          <div class="field">
                              <label>${$e("assign.ditto_count")}</label>
                              <input
                                  class="send-count"
                                  type="number"
                                  min="0"
                                  max="20"
                                  .value=${String(this._dittoCount)}
                                  title=${$e("assign.ditto_title")}
                                  @input=${this._onDittoInput}
                              />
                              <div class="hint">
                                  ${$e("assign.ditto_hint")}
                              </div>
                          </div>`:""}

                <div class="dialog-actions">
                    <button
                        class="action-btn wide cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${$e("common.cancel")}
                    </button>
                    <button
                        class="action-btn wide assign-btn"
                        @click=${this._assign}
                        ?disabled=${this._busy}
                    >
                        ${this._busy?$e("assign.assigning"):"new"===this._mode?$e("assign.create_assign"):$e("assign.assign")}
                    </button>
                </div>
            </ha-dialog>
        `}_renderExistingMode(){return F`
            <div class="field">
                <label>${$e("assign.target_device")}</label>
                ${0===this._devices.length?F`<ha-alert alert-type="info">
                          ${$e("assign.no_devices")}
                      </ha-alert>`:F`
                          <select
                              .value=${this._selectedDeviceId}
                              @change=${this._onDeviceSelected}
                          >
                              <option value="" disabled>${$e("assign.select_device")}</option>
                              ${this._devices.map(e=>F`
                                      <option
                                          value=${e.id}
                                          ?selected=${this._selectedDeviceId===e.id}
                                      >
                                          ${e.name} (${e.device_type})
                                      </option>
                                  `)}
                          </select>
                      `}
            </div>
        `}_renderNewMode(){return F`
            <div class="field">
                <label>${$e("promote.device_name")}</label>
                <input
                    type="text"
                    .value=${this._newName}
                    placeholder=${$e("common.device_name_placeholder")}
                    required
                    autofocus
                    @input=${e=>this._newName=e.target.value}
                />
            </div>

            <div class="field">
                <label>${$e("common.device_type")}</label>
                <select
                    .value=${this._newType}
                    @change=${this._onNewTypeChanged}
                >
                    ${ds.map(e=>F`
                            <option
                                value=${e.value}
                                ?selected=${this._newType===e.value}
                            >
                                ${$e(`device_type.${e.value}`)}
                            </option>
                        `)}
                </select>
            </div>

            <ir-emitter-picker
                .hass=${this.hass}
                .api=${this.api}
                .value=${this._newEmitterIds}
                ?disabled=${this._busy}
                @emitters-changed=${e=>this._newEmitterIds=e.detail.value}
            ></ir-emitter-picker>
        `}_onCommandSelect(e){const t=e.target.value;"__custom__"===t?(this._customCommand=!0,this._commandName="",this.updateComplete.then(()=>{const e=this.shadowRoot?.querySelector(".custom-cmd-input");e?.focus()})):(this._customCommand=!1,this._commandName=t)}_renderCommandPicker(){return this._customCommand?F`
                <div class="field">
                    <label>${$e("assign.command_name")}</label>
                    <div class="custom-cmd-row">
                        <input
                            class="custom-cmd-input"
                            type="text"
                            placeholder=${$e("assign.command_placeholder")}
                            .value=${this._commandName}
                            @input=${e=>this._commandName=e.target.value}
                        />
                        <button
                            class="back-link"
                            @click=${()=>{this._customCommand=!1,this._commandName=""}}
                        >${$e("common.cancel")}</button>
                    </div>
                </div>
            `:F`
            <div class="field">
                <label>${$e("assign.command_name")}</label>
                <select
                    .value=${this._commandName}
                    @change=${this._onCommandSelect}
                >
                    <option value="" disabled ?selected=${!this._commandName}>
                        ${$e("assign.select_command")}
                    </option>
                    ${this._templates.map(e=>F`
                            <option
                                value=${we(e.name)}
                                ?selected=${this._commandName===we(e.name)}
                            >
                                ${we(e.name)}
                            </option>
                        `)}
                    <option value="__custom__">${$e("assign.custom")}</option>
                </select>
            </div>
        `}};cs.styles=[Fi,a`
        input.send-count {
            width: 80px;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-size: 0.95rem;
            font-family: inherit;
            box-sizing: border-box;
        }
        input.send-count:focus {
            outline: none;
            border-color: var(--primary-color);
        }
        input.send-count:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .hint {
            margin-top: 6px;
            font-size: 0.78rem;
            color: var(--secondary-text-color);
        }
        ha-alert {
            display: block;
            margin: 8px 0;
        }

        .signal-header {
            padding: 10px 12px;
            background: var(--secondary-background-color);
            border-radius: 4px;
            margin-bottom: 12px;
        }
        .device-name {
            font-weight: 600;
            font-size: 0.95rem;
            margin-bottom: 6px;
        }
        .signal-detail {
            margin-bottom: 4px;
        }
        .diamonds {
            font-size: 0.7rem;
            letter-spacing: 0px;
            line-height: 1;
        }
        .diamond.long {
            color: var(--primary-color);
        }
        .diamond.short {
            color: var(--warning-color, #ff9800);
        }
        .proto-label {
            font-size: 0.82rem;
            font-weight: 500;
            color: var(--secondary-text-color);
        }
        .signal-stats {
            display: flex;
            gap: 12px;
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            margin-top: 4px;
        }

        .mode-tabs {
            display: flex;
            border-bottom: 1px solid var(--divider-color);
            margin: 12px 0;
        }
        .mode-tab {
            flex: 1;
            background: none;
            border: none;
            border-bottom: 2px solid transparent;
            padding: 8px 12px;
            font-size: 0.85rem;
            font-weight: 500;
            color: var(--secondary-text-color);
            cursor: pointer;
            font-family: inherit;
            transition: color 150ms ease, border-color 150ms ease;
        }
        .mode-tab:hover {
            color: var(--primary-text-color);
        }
        .mode-tab.active {
            color: var(--primary-color);
            border-bottom-color: var(--primary-color);
        }

        .assign-btn {
            background: var(--primary-color);
            color: var(--text-primary-color, #fff);
        }
        .assign-btn:hover:not(:disabled) {
            opacity: 0.9;
        }

        /* --- Custom command input --- */
        .custom-cmd-row {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        .custom-cmd-input {
            flex: 1;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
            font-family: inherit;
            font-size: 0.9rem;
        }
        .custom-cmd-input:focus {
            outline: none;
            border-color: var(--primary-color);
        }
        .back-link {
            background: none;
            border: none;
            color: var(--primary-color);
            font-size: 0.8rem;
            font-family: inherit;
            cursor: pointer;
            padding: 4px 8px;
            white-space: nowrap;
        }
        .back-link:hover {
            text-decoration: underline;
        }
    `],e([pe({attribute:!1})],cs.prototype,"api",void 0),e([pe({attribute:!1})],cs.prototype,"hass",void 0),e([pe()],cs.prototype,"unknownDeviceId",void 0),e([pe({attribute:!1})],cs.prototype,"signal",void 0),e([pe()],cs.prototype,"suggestedDeviceName",void 0),e([pe()],cs.prototype,"initialMode",void 0),e([he()],cs.prototype,"_mode",void 0),e([he()],cs.prototype,"_devices",void 0),e([he()],cs.prototype,"_selectedDeviceId",void 0),e([he()],cs.prototype,"_commandName",void 0),e([he()],cs.prototype,"_newName",void 0),e([he()],cs.prototype,"_newType",void 0),e([he()],cs.prototype,"_newEmitterIds",void 0),e([he()],cs.prototype,"_templates",void 0),e([he()],cs.prototype,"_customCommand",void 0),e([he()],cs.prototype,"_sendCount",void 0),e([he()],cs.prototype,"_dittoCount",void 0),e([he()],cs.prototype,"_busy",void 0),e([he()],cs.prototype,"_error",void 0),cs=e([me("ir-assign-signal-dialog")],cs);const ps=[{value:"media_player",label:"Media Player"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"light",label:"Light"},{value:"switch",label:"Switch"},{value:"screen",label:"Screen / Shade"},{value:"other",label:"Other"}];let hs=class extends ne{constructor(){super(...arguments),this.suggestedName="",this._name="",this._type="other",this._emitterIds=[],this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this.suggestedName&&!this._name&&(this._name=this.suggestedName)}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _create(){const e=this._name.trim();if(e)if(0!==this._emitterIds.length){this._busy=!0,this._error=null;try{await this.api.createDevice({name:e,device_type:this._type,emitter_entity_ids:this._emitterIds}),this.dispatchEvent(new CustomEvent("device-created",{bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error=$e("promote.emitter_required");else this._error=$e("promote.device_name_required")}render(){return F`
            <ha-dialog
                open
                heading=${$e("promote.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?F`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <p class="description">${$e("promote.description")}</p>

                <div class="field">
                    <label>${$e("promote.device_name")}</label>
                    <input
                        type="text"
                        .value=${this._name}
                        placeholder=${$e("common.device_name_placeholder")}
                        required
                        autofocus
                        @input=${e=>this._name=e.target.value}
                        @keydown=${e=>{"Enter"===e.key&&this._create()}}
                    />
                </div>

                <div class="field">
                    <label>${$e("common.device_type")}</label>
                    <select
                        .value=${this._type}
                        @change=${e=>this._type=e.target.value}
                    >
                        ${ps.map(e=>F`
                                <option
                                    value=${e.value}
                                    ?selected=${this._type===e.value}
                                >
                                    ${$e(`device_type.${e.value}`)}
                                </option>
                            `)}
                    </select>
                </div>

                <ir-emitter-picker
                    .hass=${this.hass}
                    .api=${this.api}
                    .value=${this._emitterIds}
                    ?disabled=${this._busy}
                    @emitters-changed=${e=>this._emitterIds=e.detail.value}
                ></ir-emitter-picker>

                <div class="dialog-actions">
                    <button
                        class="action-btn wide cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${$e("common.cancel")}
                    </button>
                    <button
                        class="action-btn wide create-btn"
                        @click=${this._create}
                        ?disabled=${this._busy}
                    >
                        ${this._busy?$e("common.creating"):$e("promote.create_device")}
                    </button>
                </div>
            </ha-dialog>
        `}};hs.styles=[Fi,a`
        /* NOTE: no ha-textfield here anymore. This dialog was the
           panel's last ha-textfield user; the element is lazy-loaded by
           the HA frontend and is not reliably defined inside a custom
           panel, so it rendered as an empty, unfocusable shell (shampoo
           bench). The name box is now the shared .field + plain input,
           the same proven pattern as every other dialog. */
        ha-alert {
            display: block;
            margin: 8px 0;
        }
        .description {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin: 0 0 8px;
        }
        .create-btn {
            background: #2e7d32;
            color: #fff;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `],e([pe({attribute:!1})],hs.prototype,"api",void 0),e([pe({attribute:!1})],hs.prototype,"hass",void 0),e([pe()],hs.prototype,"suggestedName",void 0),e([he()],hs.prototype,"_name",void 0),e([he()],hs.prototype,"_type",void 0),e([he()],hs.prototype,"_emitterIds",void 0),e([he()],hs.prototype,"_busy",void 0),e([he()],hs.prototype,"_error",void 0),hs=e([me("ir-promote-dialog")],hs);let gs=class extends ne{constructor(){super(...arguments),this.value=[],this.busy=!1,this._local=[]}connectedCallback(){super.connectedCallback(),this._local=[...this.value]}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_send(){0!==this._local.length&&this.dispatchEvent(new CustomEvent("send",{detail:{emitters:[...this._local]},bubbles:!0,composed:!0}))}_onEmittersChanged(e){this._local=e.detail.value,this.dispatchEvent(new CustomEvent("emitters-changed",{detail:{value:this._local},bubbles:!0,composed:!0}))}render(){const e=this._local.length>0&&!this.busy;return F`
            <ha-dialog
                open
                heading=${$e("test_emitter.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                <ir-emitter-picker
                    .hass=${this.hass}
                    .api=${this.api}
                    .value=${this._local}
                    ?disabled=${this.busy}
                    @emitters-changed=${this._onEmittersChanged}
                ></ir-emitter-picker>

                <div class="dialog-actions">
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this.busy}
                    >
                        ${$e("common.cancel")}
                    </button>
                    <button
                        class="action-btn send-btn"
                        @click=${this._send}
                        ?disabled=${!e}
                    >
                        ${this.busy?$e("test_emitter.sending"):$e("test_emitter.send")}
                    </button>
                </div>
            </ha-dialog>
        `}};gs.styles=[Fi,a`
        /* Slimmer actions row than the shared one; ships this way. */
        .dialog-actions {
            margin-top: 16px;
            padding-top: 0;
            border-top: none;
        }
        /* Opacity in the transition so the Send hover fades, not snaps. */
        .action-btn {
            transition: background 150ms ease, opacity 150ms ease;
        }
        /* Brighter cancel than the shared secondary; ships this way. */
        .cancel-btn {
            color: var(--primary-text-color);
        }
        .send-btn {
            background: #2e7d32;
            color: #fff;
            border-color: #2e7d32;
        }
        .send-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `],e([pe({attribute:!1})],gs.prototype,"api",void 0),e([pe({attribute:!1})],gs.prototype,"hass",void 0),e([pe({attribute:!1})],gs.prototype,"value",void 0),e([pe({type:Boolean})],gs.prototype,"busy",void 0),e([he()],gs.prototype,"_local",void 0),gs=e([me("ir-test-emitter-dialog")],gs);let ms=class extends ne{constructor(){super(...arguments),this.assignments=[],this.top=0,this.left=0}render(){return F`
            <div
                class="action-popover"
                style="top:${this.top}px; left:${this.left}px"
            >
                <div class="popover-header">${$e("popover.assigned_to")}</div>
                <button
                    class="popover-item accent"
                    @click=${()=>this._emit("create-new")}
                >
                    <span>${$e("popover.new_assignment")}</span>
                </button>
                <div class="popover-divider"></div>
                ${this.assignments.map(e=>F`
                        <button
                            class="popover-item"
                            title=${$e("popover.open_in_devices",{name:e.device_name})}
                            @click=${()=>this._emit("open-assignment",e)}
                        >
                            <span class="popover-name"
                                >${e.device_name} / ${e.command_name}</span
                            >
                            <ha-svg-icon
                                class="chevron"
                                .path=${"M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z"}
                            ></ha-svg-icon>
                        </button>
                    `)}
            </div>
        `}_emit(e,t){this.dispatchEvent(new CustomEvent(e,{detail:t,bubbles:!0,composed:!0}))}};ms.styles=[Ki,a`
            :host {
                display: contents;
            }
            .chevron {
                --mdc-icon-size: 14px;
                color: var(--secondary-text-color);
                flex: none;
            }
        `],e([pe({attribute:!1})],ms.prototype,"assignments",void 0),e([pe({type:Number})],ms.prototype,"top",void 0),e([pe({type:Number})],ms.prototype,"left",void 0),ms=e([me("ir-assigned-popover")],ms);const us="hair-mirror";function _s(e,t){const i=e.decoded_fingerprint??null,s=t.decoded_fingerprint??null;if(null!==i&&null!==s)return i===s;const r=e.byte_hash??null,o=t.byte_hash??null;return null!==r&&null!==o?r===o:e.signal_fingerprint===t.fingerprint}var vs;function bs(e){try{return new Date(e).toLocaleString(xe(),{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return e}}function fs(e){try{const t=Date.now()-new Date(e).getTime();return t<6e4?$e("rel.just_now"):t<36e5?$e("rel.min_ago",{count:Math.floor(t/6e4)}):t<864e5?$e("rel.h_ago",{count:Math.floor(t/36e5)}):$e("rel.d_ago",{count:Math.floor(t/864e5)})}catch{return""}}const ys="M12 9.188c-1.553 0-2.812 1.259-2.812 2.812s1.259 2.812 2.812 2.812c1.553 0 2.812-1.259 2.812-2.812v0c-0.002-1.552-1.26-2.81-2.812-2.812h-0zM12 13.688c-0.932 0-1.688-0.755-1.688-1.688s0.755-1.688 1.688-1.688c0.932 0 1.688 0.755 1.688 1.688v0c-0.002 0.931-0.756 1.686-1.688 1.688h-0zM2.062 12c0.16-2.665 1.25-5.049 2.948-6.856l-0.005 0.006c0.098-0.101 0.159-0.239 0.159-0.392 0-0.31-0.252-0.562-0.562-0.562-0.153 0-0.291 0.061-0.393 0.16l0-0c-1.906 1.998-3.125 4.667-3.27 7.618l-0.001 0.028c0.146 2.979 1.365 5.647 3.275 7.652l-0.005-0.005c0.101 0.098 0.239 0.159 0.392 0.159 0.31 0 0.562-0.252 0.562-0.562 0-0.152-0.061-0.291-0.16-0.392l0 0c-1.694-1.8-2.785-4.185-2.94-6.821l-0.002-0.03zM6.647 12c0.113-1.859 0.874-3.523 2.058-4.784l-0.004 0.004c0.098-0.101 0.159-0.239 0.159-0.392 0-0.31-0.252-0.562-0.562-0.562-0.153 0-0.291 0.061-0.392 0.16l0-0c-1.39 1.457-2.278 3.403-2.383 5.554l-0.001 0.02c0.105 2.171 0.994 4.117 2.386 5.577l-0.003-0.004c0.102 0.104 0.244 0.167 0.4 0.167 0.31 0 0.562-0.251 0.562-0.562 0-0.156-0.064-0.297-0.167-0.399l-0-0c-1.183-1.256-1.944-2.92-2.053-4.759l-0.001-0.021zM19.793 4.355c-0.102-0.101-0.241-0.164-0.396-0.164-0.31 0-0.562 0.252-0.562 0.562 0 0.154 0.062 0.294 0.162 0.395l-0-0c1.691 1.802 2.782 4.185 2.94 6.82l0.002 0.03c-0.16 2.665-1.249 5.05-2.947 6.857l0.005-0.006c-0.105 0.102-0.17 0.244-0.17 0.403 0 0.31 0.252 0.562 0.562 0.562 0.158 0 0.301-0.065 0.404-0.171l0-0c1.906-1.999 3.125-4.667 3.268-7.618l0.001-0.028c-0.146-2.978-1.364-5.647-3.274-7.65l0.005 0.005zM15.299 6.425c-0.102 0.102-0.165 0.242-0.165 0.398 0 0.154 0.062 0.295 0.164 0.397l-0-0c1.181 1.257 1.942 2.92 2.054 4.758l0.001 0.022c-0.114 1.86-0.875 3.523-2.059 4.784l0.004-0.004c-0.101 0.102-0.164 0.241-0.164 0.396 0 0.311 0.252 0.563 0.563 0.563 0.155 0 0.295-0.062 0.397-0.164l-0 0c1.389-1.458 2.277-3.404 2.383-5.555l0.001-0.02c-0.105-2.172-0.994-4.118-2.388-5.578l0.003 0.003c-0.101-0.102-0.242-0.165-0.397-0.165s-0.295 0.063-0.397 0.165l-0 0z",xs="M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z";let $s=vs=class extends ne{constructor(){super(...arguments),this._devices=[],this._hairDevices=[],this._loading=!0,this._error=null,this._hasReceivers=!0,this._showDismissed=!1,this._expandedId=null,this._expandedDevice=null,this._flashIds=new Set,this._flashStats=new Set,this._recentSignalIds=[],this._glowSignalIds=new Set,this._hitFlashSignalIds=new Set,this._confirmClearAll=!1,this._triggers=[],this._triggerDialog=null,this._triggerEditDialog=null,this._confirmDeleteTriggerId=null,this._triggerPopover=null,this._assignedPopover=null,this._receivers=[],this._unsubUpdated=null,this._editingDeviceId=null,this._editLabel="",this._promoteTarget=null,this._assignSignal=null,this._deleteSignal=null,this._editSignal=null,this._testingSignalId=null,this._testResult=null,this._testDialog=null,this._testEmitters=[],this._dismissGlowActive=!1,this._dismissDotVisible=!1,this._unsubLive=null,this._unsubRemoved=null,this._unsubDismiss=null,this._dismissGlowTimer=null,this._remotesVersion=0,this._signalsVersion=0,this._remotesSortable=null,this._signalsSortable=null,this._signalsSortableContainer=null,this._pendingRemotesSave=null,this._pendingSignalsSave=null,this._onDocClickForPopover=e=>{const t=e.composedPath(),i=this.shadowRoot?.querySelector("ir-trigger-popover"),s=this.shadowRoot?.querySelector("ir-assigned-popover");i&&t.includes(i)||s&&t.includes(s)||(this._closeTriggerPopover(),this._closeAssignedPopover())},this._onScrollForPopover=()=>{this._closeTriggerPopover(),this._closeAssignedPopover()}}connectedCallback(){super.connectedCallback(),this._load(),this._subscribeLive(),this._subscribeRemoved(),this._subscribeDismissActivity(),this._subscribeUpdated()}updated(e){if(super.updated(e),e.has("_editingDeviceId")&&this._editingDeviceId){const e=this.shadowRoot?.querySelector(".rename-input");e&&(e.focus(),e.select())}this._syncSortables()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeLive(),this._unsubscribeRemoved(),this._unsubscribeDismissActivity(),this._unsubscribeUpdated(),this._removePopoverDismiss(),null!==this._dismissGlowTimer&&(clearTimeout(this._dismissGlowTimer),this._dismissGlowTimer=null),this._remotesSortable?.destroy(),this._remotesSortable=null,this._signalsSortable?.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null,null!==this._pendingRemotesSave&&clearTimeout(this._pendingRemotesSave),null!==this._pendingSignalsSave&&clearTimeout(this._pendingSignalsSave)}_syncSortables(){const e=this.renderRoot.querySelector(".device-list");e&&!this._remotesSortable?this._attachRemotesSortable(e):!e&&this._remotesSortable&&(this._remotesSortable.destroy(),this._remotesSortable=null);const t=this.renderRoot.querySelector(".signal-list"),i=!!this._expandedDevice&&!this._expandedDevice.dismissed;!t||!i||this._signalsSortable&&this._signalsSortableContainer===t?t&&i||!this._signalsSortable||(this._signalsSortable.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null):(this._signalsSortable?.destroy(),this._attachSignalsSortable(t))}_attachRemotesSortable(e){this._remotesSortable=bi.create(e,{handle:".remote-grip",animation:150,ghostClass:"sortable-ghost",onEnd:t=>{const{oldIndex:i,newIndex:s}=t;if(void 0===i||void 0===s||i===s)return;const r=[...this._devices],[o]=r.splice(i,1);r.splice(s,0,o),this._devices=r,this._remotesSortable?.destroy(),this._remotesSortable=null,this._purgeChildren(e,"ha-card"),this._remotesVersion++,this._scheduleRemotesSave(r.map(e=>e.id))}})}_attachSignalsSortable(e){this._expandedDevice&&(this._signalsSortableContainer=e,this._signalsSortable=bi.create(e,{handle:".signal-grip",animation:150,ghostClass:"sortable-ghost",onEnd:t=>{const{oldIndex:i,newIndex:s}=t;if(void 0===i||void 0===s||i===s)return;const r=this._expandedDevice;if(!r)return;const o=[...r.signals],[a]=o.splice(i,1);o.splice(s,0,a),this._expandedDevice={...r,signals:o},this._signalsSortable?.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null,this._purgeChildren(e,".signal-row"),this._signalsVersion++,this._scheduleSignalsSave(r.id,o.map(e=>e.id))}}))}_purgeChildren(e,t){for(const i of Array.from(e.querySelectorAll(t)))i.remove()}_scheduleRemotesSave(e){null!==this._pendingRemotesSave&&clearTimeout(this._pendingRemotesSave),this._pendingRemotesSave=window.setTimeout(async()=>{this._pendingRemotesSave=null;try{await this.api.reorderUnknownDevices("sniffed",e)}catch(e){this._error=`Reorder failed: ${e.message}`,await this._load()}},500)}_scheduleSignalsSave(e,t){null!==this._pendingSignalsSave&&clearTimeout(this._pendingSignalsSave),this._pendingSignalsSave=window.setTimeout(async()=>{this._pendingSignalsSave=null;try{await this.api.reorderUnknownSignals(e,t)}catch(e){this._error=`Reorder failed: ${e.message}`}},500)}async _load(){this._loading=!0;try{const[e,t,i,s]=await Promise.all([this.api.getUnknownDevices({include_dismissed:this._showDismissed,source:"sniffed"}),this.api.listDevices(),this.api.listTriggers(),this.api.getSnifferStatus()]);this._devices=e,this._hairDevices=t,this._triggers=i,this._hasReceivers=s.has_receivers,this._error=null,this.api.listReceivers().then(e=>{this._receivers=e}).catch(()=>{this._receivers=[]})}catch(e){this._error=`Failed to load: ${e.message}`}finally{this._loading=!1}}_matchesHairDevice(e){if(!e)return!1;const t=e.toLowerCase();return this._hairDevices.some(e=>e.name.toLowerCase()===t)}async _subscribeLive(){try{this._unsubLive=await this.api.subscribeUnknownSignals(e=>{this._onLiveSignal(e)})}catch{}}async _unsubscribeLive(){this._unsubLive&&(await this._unsubLive(),this._unsubLive=null)}async _subscribeRemoved(){try{this._unsubRemoved=await this.api.subscribeSignalRemoved(e=>{this._load(),this._expandedId===e.device_id&&(e.device_removed?(this._expandedId=null,this._expandedDevice=null):(this._toggleExpand(e.device_id),this._toggleExpand(e.device_id)))})}catch{}}async _unsubscribeRemoved(){this._unsubRemoved&&(await this._unsubRemoved(),this._unsubRemoved=null)}async _subscribeDismissActivity(){try{this._unsubDismiss=await this.api.subscribeDismissActivity(()=>this._onDismissActivity())}catch{}}async _unsubscribeDismissActivity(){this._unsubDismiss&&(await this._unsubDismiss(),this._unsubDismiss=null)}_onDismissActivity(){this._dismissDotVisible=!0,this._dismissGlowActive=!0,null!==this._dismissGlowTimer&&clearTimeout(this._dismissGlowTimer),this._dismissGlowTimer=setTimeout(()=>{this._dismissGlowActive=!1,this._dismissGlowTimer=null},vs.DISMISS_GLOW_HOLD_MS)}_startRename(e,t){t.stopPropagation(),this._editingDeviceId=e.id,this._editLabel=e.label??e.protocol??""}async _commitRename(e){const t=this._editLabel.trim();this._editingDeviceId=null;try{const i=await this.api.renameUnknown(e,t),s=this._devices.findIndex(t=>t.id===e);if(s>=0){const e=[...this._devices];e[s]={...e[s],label:i.label},this._devices=e}}catch(e){this._error=`Rename failed: ${e.message}`}}_cancelRename(){this._editingDeviceId=null}_onRenameKeydown(e,t){"Enter"===t.key?this._commitRename(e):"Escape"===t.key&&this._cancelRename()}_promoteDevice(e,t){t.stopPropagation(),this._promoteTarget=e}_closePromote(){this._promoteTarget=null}async _onDevicePromoted(){this._promoteTarget=null,await this._load()}_openAssign(e,t,i,s){this._assignSignal={deviceId:e,signal:t,label:i??null,initialMode:s??"existing"}}_onAssignClick(e,t,i,s){if(!t.assigned_to?.length)return void this._openAssign(e,t,i);const r=s?.currentTarget,o=r?.getBoundingClientRect();this._assignedPopover={deviceId:e,signal:t,label:i??null,top:o?o.bottom+4:120,left:o?Math.max(8,o.right-220):120},this._installPopoverDismiss()}_closeAssignedPopover(){this._assignedPopover=null,this._removePopoverDismiss()}_onAssignedPopoverCreateNew(){const e=this._assignedPopover;this._closeAssignedPopover(),e&&this._openAssign(e.deviceId,e.signal,e.label)}_onAssignedPopoverOpen(e){const t=e.detail;this._closeAssignedPopover(),t&&this.dispatchEvent(new CustomEvent("navigate-device",{detail:t.device_id,bubbles:!0,composed:!0}))}_closeAssign(){this._assignSignal=null}async _onSignalAssigned(e){if(this._assignSignal=null,await this._load(),this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{this._expandedId=null,this._expandedDevice=null}}_openDelete(e,t){this._deleteSignal={deviceId:e,signal:t}}_closeDelete(){this._deleteSignal=null}_openEditSignal(e,t,i){i.stopPropagation(),this._editSignal={deviceId:e,signal:t}}async _onSignalEdited(){if(this._editSignal=null,await this._load(),this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{this._expandedId=null,this._expandedDevice=null}}async _confirmDelete(){if(!this._deleteSignal)return;const{deviceId:e,signal:t}=this._deleteSignal;this._deleteSignal=null;try{await this.api.deleteSignal(e,t.id),await this._load()}catch(e){this._error=`Delete failed: ${e.message}`}}_openTestDialog(e){this._testDialog={signal:e}}_closeTestDialog(){this._testDialog=null}async _sendTest(e){if(!this._testDialog)return;const{signal:t}=this._testDialog,i=e.detail.emitters;if(0!==i.length){this._testingSignalId=t.id,this._testResult=null,this._testDialog=null;try{const e=(await Promise.allSettled(i.map(e=>this.api.testSignal(t.id,e)))).filter(e=>"fulfilled"===e.status&&e.value.sent).length,s=i.length;this._testResult=e===s?1===s?$e("mirror.sent"):$e("mirror.sent_all_n",{sent:e,total:s}):0===e?$e("mirror.failed"):`Sent (${e}/${s})`}catch{this._testResult="Error"}setTimeout(()=>{this._testResult=null,this._testingSignalId=null},3e3)}}_hasTrigger(e){return this._triggers.some(t=>_s(t,e))}_triggerCountFor(e){return this._triggers.filter(t=>_s(t,e)).length}_openTriggerDialog(e,t,i){const s=this._triggers.filter(e=>_s(e,t));if(0===s.length)return void(this._triggerDialog={signal:t,deviceId:e});const r=i?.currentTarget,o=r?.getBoundingClientRect();this._triggerPopover={deviceId:e,signal:t,top:o?o.bottom+4:120,left:o?Math.max(8,o.right-220):120},this._installPopoverDismiss()}_closeTriggerPopover(){this._triggerPopover=null,this._removePopoverDismiss()}_onPopoverCreateNew(){const e=this._triggerPopover;this._closeTriggerPopover(),e&&(this._triggerDialog={signal:e.signal,deviceId:e.deviceId})}_onPopoverEditTrigger(e){const t=e.detail;this._closeTriggerPopover(),t&&(this._triggerEditDialog=t)}_installPopoverDismiss(){setTimeout(()=>{document.addEventListener("click",this._onDocClickForPopover,!0),window.addEventListener("scroll",this._onScrollForPopover,!0)},0)}_removePopoverDismiss(){document.removeEventListener("click",this._onDocClickForPopover,!0),window.removeEventListener("scroll",this._onScrollForPopover,!0)}async _subscribeUpdated(){try{this._unsubUpdated=await this.api.subscribeSignalUpdated(()=>{this._refreshAfterSignalUpdate()})}catch{}}async _unsubscribeUpdated(){this._unsubUpdated&&(await this._unsubUpdated(),this._unsubUpdated=null)}async _refreshAfterSignalUpdate(){try{this._triggers=await this.api.listTriggers()}catch{}if(this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{}}_closeTriggerDialog(){this._triggerDialog=null,this._triggerEditDialog=null}_requestDeleteTrigger(e){this._confirmDeleteTriggerId=e}async _doDeleteTrigger(){if(!this._confirmDeleteTriggerId)return;const e=this._confirmDeleteTriggerId;this._confirmDeleteTriggerId=null,this._triggerEditDialog=null;try{await this.api.deleteTrigger(e),this._triggers=await this.api.listTriggers()}catch{}}async _onTriggerSaved(){this._triggerDialog=null,this._triggerEditDialog=null;try{this._triggers=await this.api.listTriggers()}catch{}}_onLiveSignal(e){if(e.device_fingerprint===us)return;const t=(new Date).toISOString(),i=this._devices.findIndex(t=>t.id===e.device_id);if(i>=0){{const s={...this._devices[i]};s.hit_count=e.device_hit_count??e.hit_count,s.last_seen=t,1===e.hit_count&&(s.signal_count=(s.signal_count??0)+1);const r=[...this._devices];r[i]=s,this._devices=r}if(this._expandedDevice&&this._expandedId===e.device_id){const i=this._expandedDevice.signals.findIndex(t=>t.id===e.signal_id);if(i>=0){const s={...this._expandedDevice.signals[i]};s.hit_count=e.hit_count,s.last_seen=t;const r=[...this._expandedDevice.signals];r[i]=s,this._expandedDevice={...this._expandedDevice,hit_count:e.device_hit_count??e.hit_count,last_seen:t,signals:r}}else this.api.getUnknownDevice(e.device_id).then(t=>{if(this._expandedId===e.device_id){this._expandedDevice=t;const i=this._devices.findIndex(t=>t.id===e.device_id);if(i>=0){const e={...this._devices[i],signal_count:t.signals.length},s=[...this._devices];s[i]=e,this._devices=s}}}).catch(()=>{})}if(this._flashIds=new Set([...this._flashIds,e.device_id]),setTimeout(()=>{const t=new Set(this._flashIds);t.delete(e.device_id),this._flashIds=t},800),this._flashStats=new Set([...this._flashStats,e.device_id]),setTimeout(()=>{const t=new Set(this._flashStats);t.delete(e.device_id),this._flashStats=t},1500),e.signal_id){const t=[e.signal_id,...this._recentSignalIds.filter(t=>t!==e.signal_id)].slice(0,2);this._recentSignalIds=t,this._glowSignalIds=new Set([...this._glowSignalIds,e.signal_id]),setTimeout(()=>{const t=new Set(this._glowSignalIds);t.delete(e.signal_id),this._glowSignalIds=t},1200),this._hitFlashSignalIds=new Set([...this._hitFlashSignalIds,e.signal_id]),setTimeout(()=>{const t=new Set(this._hitFlashSignalIds);t.delete(e.signal_id),this._hitFlashSignalIds=t},1200)}}else this._load()}_onAliasChanged(e){const{id:t,alias:i}=e.detail;this._expandedDevice&&(this._expandedDevice={...this._expandedDevice,signals:this._expandedDevice.signals.map(e=>e.id===t?{...e,alias:i}:e)})}async _toggleExpand(e){if(this._expandedId===e)return this._expandedId=null,void(this._expandedDevice=null);this._expandedId=e;try{this._expandedDevice=await this.api.getUnknownDevice(e)}catch{this._expandedDevice=null}}async _dismiss(e){try{await this.api.dismissUnknown(e),await this._load(),this._expandedId===e&&(this._expandedId=null,this._expandedDevice=null)}catch(e){this._error=`Dismiss failed: ${e.message}`}}async _undismiss(e){try{await this.api.undismissUnknown(e),await this._load()}catch(e){this._error=`Restore failed: ${e.message}`}}async _doClearAll(){this._confirmClearAll=!1;try{await this.api.clearUnknowns(),this._devices=[],this._expandedId=null,this._expandedDevice=null}catch(e){this._error=`Clear failed: ${e.message}`}}_toggleDismissed(){this._showDismissed=!this._showDismissed,this._dismissDotVisible=!1,this._load()}render(){return F`
            <div class="toolbar">
                <span class="title">
                    <ha-svg-icon .path=${ys}></ha-svg-icon>
                    ${$e("sniffer.title")}
                    ${this._loading?"":F`<span class="count"
                              >(${ke("sniffer.remotes",this._devices.length)})</span
                          >`}
                </span>
            </div>

            ${this._error?F`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

            ${this._loading?F`<div class="loading">${$e("sniffer.scanning")}</div>`:0===this._devices.length?this._hasReceivers?F`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${ys}></ha-svg-icon>
                            <h3>${$e("sniffer.empty_title")}</h3>
                            <p>${$e("sniffer.empty_body")}</p>
                            <p class="hint">${$e("sniffer.empty_hint")}</p>
                        </ha-card>
                    `:F`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${ys}></ha-svg-icon>
                            <h3>${$e("sniffer.norx_title")}</h3>
                            <p>${$e("sniffer.norx_body")}</p>
                            <p class="hint">${$e("sniffer.norx_hint")}</p>
                        </ha-card>
                    `:F`
                        <div class="device-list">
                            ${He(this._remotesVersion,Ne(this._devices,e=>e.id,e=>this._renderDevice(e)))}
                        </div>
                    `}

            <div class="bottom-bar">
                <button
                    class="action-btn dismiss-btn ${this._dismissGlowActive?"dismiss-glow":""}"
                    title=${$e("sniffer.show_dismissed_title")}
                    @click=${this._toggleDismissed}
                >
                    ${this._showDismissed?$e("sniffer.hide_dismissed"):$e("sniffer.show_dismissed")}
                    ${this._dismissDotVisible?F`<span class="dismiss-dot" aria-hidden="true"></span>`:""}
                </button>
                ${this._devices.length>0||this._showDismissed?F`<button
                          class="action-btn delete-btn"
                          title=${$e("sniffer.clear_all_title")}
                          @click=${()=>this._confirmClearAll=!0}
                      >
                          ${$e("sniffer.clear_all")}
                      </button>`:""}
            </div>

            ${this._assignSignal?F`
                      <ir-assign-signal-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .unknownDeviceId=${this._assignSignal.deviceId}
                          .signal=${this._assignSignal.signal}
                          .suggestedDeviceName=${this._assignSignal.label??""}
                          .initialMode=${this._assignSignal.initialMode}
                          @signal-assigned=${this._onSignalAssigned}
                          @closed=${this._closeAssign}
                      ></ir-assign-signal-dialog>
                  `:""}

            ${this._promoteTarget?F`
                      <ir-promote-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .suggestedName=${this._promoteTarget.label??""}
                          @device-created=${this._onDevicePromoted}
                          @closed=${this._closePromote}
                      ></ir-promote-dialog>
                  `:""}

            ${this._deleteSignal?F`
                      <ir-confirm-dialog
                          title=${$e("sniffer.del_signal_title")}
                          message=${$e("sniffer.del_signal_msg")}
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._confirmDelete}
                          @closed=${this._closeDelete}
                      ></ir-confirm-dialog>
                  `:""}

            ${this._editSignal?F`<ir-signal-editor
                      .api=${this.api}
                      .deviceId=${this._editSignal.deviceId}
                      .signalId=${this._editSignal.signal.id}
                      .initialPronto=${this._editSignal.signal.code??""}
                      .initialAlias=${this._editSignal.signal.alias??""}
                      .initialSendCount=${this._editSignal.signal.send_count??1}
                      .initialDitto=${this._editSignal.signal.repeat_count??1}
                      .initialObservedRepeatCount=${this._editSignal.signal.observed_repeat_count??0}
                      .allowSnap=${!0}
                      @signal-edited=${this._onSignalEdited}
                      @closed=${()=>this._editSignal=null}
                  ></ir-signal-editor>`:""}

            ${this._confirmClearAll?F`
                      <ir-confirm-dialog
                          title=${$e("sniffer.clear_all_confirm_title")}
                          message=${$e("sniffer.clear_all_confirm_msg")}
                          confirmLabel="Clear All"
                          .destructive=${!0}
                          @confirmed=${this._doClearAll}
                          @closed=${()=>this._confirmClearAll=!1}
                      ></ir-confirm-dialog>
                  `:""}

            ${this._triggerPopover?F`
                      <ir-trigger-popover
                          .triggers=${this._triggers.filter(e=>_s(e,this._triggerPopover.signal))}
                          .receivers=${this._receivers}
                          .top=${this._triggerPopover.top}
                          .left=${this._triggerPopover.left}
                          @create-new=${this._onPopoverCreateNew}
                          @edit-trigger=${this._onPopoverEditTrigger}
                      ></ir-trigger-popover>
                  `:""}
            ${this._assignedPopover?F`
                      <ir-assigned-popover
                          .assignments=${this._assignedPopover.signal.assigned_to??[]}
                          .top=${this._assignedPopover.top}
                          .left=${this._assignedPopover.left}
                          @create-new=${this._onAssignedPopoverCreateNew}
                          @open-assignment=${this._onAssignedPopoverOpen}
                      ></ir-assigned-popover>
                  `:""}
            ${this._triggerDialog?F`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .signalFingerprint=${this._triggerDialog.signal.fingerprint}
                          .byteHash=${this._triggerDialog.signal.byte_hash??null}
                          .decodedFingerprint=${this._triggerDialog.signal.decoded_fingerprint??null}
                          .protocol=${this._triggerDialog.signal.protocol}
                          .code=${this._triggerDialog.signal.code}
                          .slPattern=${this._triggerDialog.signal.sl_pattern??null}
                          .alias=${this._triggerDialog.signal.alias||null}
                          @trigger-saved=${this._onTriggerSaved}
                          @closed=${this._closeTriggerDialog}
                      ></ir-trigger-dialog>
                  `:""}
            ${this._testDialog?F`
                      <ir-test-emitter-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .value=${this._testEmitters}
                          @emitters-changed=${e=>this._testEmitters=e.detail.value}
                          @send=${this._sendTest}
                          @closed=${this._closeTestDialog}
                      ></ir-test-emitter-dialog>
                  `:""}
            ${this._triggerEditDialog?F`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .trigger=${this._triggerEditDialog}
                          @trigger-saved=${this._onTriggerSaved}
                          @closed=${this._closeTriggerDialog}
                          @trigger-delete=${e=>this._requestDeleteTrigger(e.detail.triggerId)}
                      ></ir-trigger-dialog>
                  `:""}
            ${this._confirmDeleteTriggerId?F`
                      <ir-confirm-dialog
                          title=${$e("mirror.del_trigger_title")}
                          message=${$e("devdetail.del_trigger_msg")}
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._doDeleteTrigger}
                          @closed=${()=>this._confirmDeleteTriggerId=null}
                      ></ir-confirm-dialog>
                  `:""}
        `}_renderDevice(e){const t=this._expandedId===e.id,i=this._flashIds.has(e.id),s=this._flashStats.has(e.id);return F`
            <ha-card class="device ${e.dismissed?"dismissed":""}">
                <div
                    class="device-row ${i?"flash-row":""}"
                    @click=${()=>this._toggleExpand(e.id)}
                >
                    <div class="device-info">
                        <div class="device-header">
                            ${this._editingDeviceId===e.id?F`<input
                                      class="rename-input"
                                      type="text"
                                      .value=${this._editLabel}
                                      @input=${e=>{this._editLabel=e.target.value}}
                                      @keydown=${t=>this._onRenameKeydown(e.id,t)}
                                      @blur=${()=>{this._commitRename(e.id)}}
                                      @click=${e=>e.stopPropagation()}
                                  />`:F`<ha-svg-icon
                                          class="remote-grip"
                                          .path=${xs}
                                          title=${$e("devdetail.drag")}
                                          @click=${e=>e.stopPropagation()}
                                      ></ha-svg-icon>
                                      ${e.dismissed?F`<span class="protocol locked"
                                                >${e.label??e.protocol??$e("common.raw")}</span
                                            >`:F`<span
                                                class="protocol"
                                                title=${$e("cmdrow.rename")}
                                                @click=${t=>this._startRename(e,t)}
                                            >${e.label??e.protocol??$e("common.raw")}</span>`}`}
                            <span class="device-stats ${s?"stats-flash":""}">
                                <span class="stat"
                                    ><strong>${e.hit_count}</strong>
                                    ${ke("sniffer.hit_word",e.hit_count)}</span
                                >
                                <span class="stat"
                                    ><strong>${e.signal_count}</strong>
                                    ${ke("sniffer.signal_word",e.signal_count)}</span
                                >
                                <span class="stat last-seen" title=${bs(e.last_seen)}>${fs(e.last_seen)}</span>
                            </span>
                            ${e.label&&this._matchesHairDevice(e.label)?F`<span
                                      class="status-badge hair-device"
                                      @click=${e=>e.stopPropagation()}
                                  >${$e("sniffer.hair_device")}</span>`:e.label&&!e.dismissed?F`<span
                                          class="status-badge promote-badge"
                                          @click=${t=>this._promoteDevice(e,t)}
                                      >${$e("sniffer.promote")}</span>`:""}
                            ${e.device_address?F`<span class="address">${$e("sniffer.addr",{address:e.device_address})}</span>`:""}
                            ${e.dismissed?F`<span class="dismissed-badge">${$e("sniffer.dismissed")}</span>`:""}
                        </div>
                    </div>
                    ${e.dismissed?F`<button
                              class="action-btn device-dismiss-btn"
                              @click=${t=>{t.stopPropagation(),this._undismiss(e.id)}}
                          >${$e("sniffer.restore")}</button>`:F`<button
                              class="action-btn device-dismiss-btn"
                              @click=${t=>{t.stopPropagation(),this._dismiss(e.id)}}
                          >${$e("sniffer.dismiss")}</button>`}
                    <ha-svg-icon
                        class="expand-icon"
                        .path=${t?"M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z":"M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z"}
                    ></ha-svg-icon>
                </div>

                ${t&&this._expandedDevice?this._renderExpanded(this._expandedDevice):""}
            </ha-card>
        `}_renderExpanded(e){return F`
            <div class="expanded">
                <div class="signal-header">
                    <span>${$e("sniffer.signals_head",{count:e.signals.length})}</span>
                    <span class="first-seen">${$e("sniffer.first_seen",{time:bs(e.first_seen)})}</span>
                </div>
                <div class="signal-list">
                    ${He(this._signalsVersion,Ne(e.signals,e=>e.id,t=>{const i=this._recentSignalIds.indexOf(t.id),s=0===i,r=1===i,o=this._glowSignalIds.has(t.id),a=this._hitFlashSignalIds.has(t.id);return F`
                            <div class="signal-row">
                                ${e.dismissed?"":F`<ha-svg-icon
                                          class="signal-grip"
                                          .path=${xs}
                                          title=${$e("devdetail.drag")}
                                      ></ha-svg-icon>`}
                                <div class="signal-info">
                                    <ir-signal-alias
                                        .api=${this.api}
                                        .deviceId=${e.id}
                                        .signal=${t}
                                        ?disabled=${e.dismissed}
                                        @alias-changed=${this._onAliasChanged}
                                    ></ir-signal-alias>
                                </div>
                                <div class="signal-meta">
                                    <span class="${a?"hit-flash":""}"
                                        >${t.hit_count}
                                        ${ke("sniffer.hit_word",t.hit_count)}</span
                                    >
                                    <span title=${bs(t.last_seen)}
                                        >${fs(t.last_seen)}</span
                                    >
                                    <span>${Math.round(t.frequency/1e3)} kHz</span>
                                </div>
                                ${t.code?F`<button
                                          ?disabled=${e.dismissed}
                                          title=${$e("cmdrow.edit_code")}
                                          @click=${i=>this._openEditSignal(e.id,t,i)}
                                          style="background:none;border:none;cursor:pointer;color:var(--secondary-text-color);padding:2px;display:inline-flex;align-items:center"
                                      >
                                          <ha-svg-icon
                                              .path=${"M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"}
                                              style="--mdc-icon-size:10px"
                                          ></ha-svg-icon>
                                      </button>`:""}
                                <div class="signal-actions">
                                    <button
                                        class="action-btn assign-btn ${s?"recent-latest":""} ${r?"recent-previous":""} ${o?"glow":""}"
                                        @click=${i=>{i.stopPropagation(),this._onAssignClick(e.id,t,e.label,i)}}
                                        ?disabled=${e.dismissed}
                                        title=${t.assignment_count&&t.assigned_to?.length?1===t.assignment_count?$e("mirror.assigned_one",{device:t.assigned_to[0].device_name,command:t.assigned_to[0].command_name}):$e("mirror.assigned_n",{count:t.assignment_count})+`\n- ${t.assigned_to.map(e=>`${e.device_name} / ${e.command_name}`).join("\n- ")}`:e.dismissed?$e("sniffer.restore_first"):$e("mirror.assign_title")}
                                    >${$e("assign.assign")}<ir-count-dot
                                            color="green"
                                            .count=${t.assignment_count??0}
                                        ></ir-count-dot></button>
                                    <button
                                        class="action-btn test-btn"
                                        @click=${e=>{e.stopPropagation(),this._openTestDialog(t)}}
                                        ?disabled=${e.dismissed||this._testingSignalId===t.id}
                                        title=${e.dismissed?$e("sniffer.restore_first"):$e("mirror.test_title")}
                                    >${this._testingSignalId===t.id?this._testResult??$e("mirror.sending"):$e("mirror.test")}</button>
                                    <button
                                        class="action-btn trigger-btn"
                                        @click=${i=>{i.stopPropagation(),this._openTriggerDialog(e.id,t,i)}}
                                        ?disabled=${e.dismissed}
                                        title=${this._hasTrigger(t)?$e("mirror.trigger_edit"):e.dismissed?$e("sniffer.restore_first"):$e("sniffer.trigger_create")}
                                    >${$e("cmdrow.trigger")}<ir-count-dot
                                            color="yellow"
                                            .count=${this._triggerCountFor(t)}
                                        ></ir-count-dot></button>
                                    <button
                                        class="action-btn delete-btn"
                                        @click=${i=>{i.stopPropagation(),this._openDelete(e.id,t)}}
                                    >${$e("common.delete")}</button>
                                </div>
                            </div>
                        `}))}
                </div>
            </div>
        `}};$s.DISMISS_GLOW_HOLD_MS=3800,$s.styles=[Vi,a`
        :host {
            display: block;
        }

        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--primary-text-color);
        }
        .title ha-svg-icon {
            --mdc-icon-size: 24px;
            color: var(--primary-color);
        }
        .count {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
        }
        .toolbar-actions {
            display: flex;
            gap: 8px;
        }

        /* Clear All anchor below the unknown-devices list.
           Moved out of the top toolbar in v0.2.1 to pair visually with
           the new "Clear All also wipes the dismiss list" semantic, and
           to force the user to scroll past what they are about to delete
           before pressing the destructive button. */
        .clear-all-row {
            display: flex;
            justify-content: flex-end;
            margin-top: 16px;
        }
        /* Show Dismissed stacked above Clear All, both right-aligned. */
        .bottom-bar {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 8px;
            margin-top: 16px;
        }

        .loading,
        .empty {
            padding: 48px 24px;
            text-align: center;
            color: var(--secondary-text-color);
        }
        .empty-icon {
            --mdc-icon-size: 48px;
            color: var(--disabled-text-color);
            margin-bottom: 16px;
        }
        .empty h3 {
            color: var(--primary-text-color);
            margin: 8px 0;
        }
        .hint {
            font-size: 0.85rem;
            font-style: italic;
        }

        .device-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .device {
            transition: box-shadow 200ms ease;
            /* Clip the row's rectangular hover highlight to the card's
               rounded corners so it does not poke past the border stroke. */
            overflow: hidden;
            /* Subtle stroke in the Sniffer's accent blue (the radio-icon
               colour) at the same 0.3 as the Clips copper stroke. The
               rgba line is a fallback for webviews without color-mix. */
            border: 1px solid rgba(33, 150, 243, 0.3);
            border-color: color-mix(in srgb, var(--primary-color) 30%, transparent);
        }
        /* Hit flash: pulse the device-row background. When the card is
           collapsed the row fills the whole card (the card's overflow:hidden
           clips the pulse to the rounded corners), so the entire card appears
           to flash; when expanded only the top row flashes, leaving the signal
           list below calm. */
        .device-row.flash-row {
            animation: row-flash 900ms ease-out;
        }
        @keyframes row-flash {
            0% { background: transparent; }
            18% {
                background: rgba(33, 150, 243, 0.32);
                background: color-mix(in srgb, var(--primary-color) 32%, transparent);
            }
            100% { background: transparent; }
        }
        .device.dismissed {
            opacity: 0.6;
        }

        .device-row {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            cursor: pointer;
            gap: 12px;
        }
        .device-row:hover {
            background: var(--secondary-background-color);
        }
        .device-info {
            flex: 1;
            min-width: 0;
        }
        .device-header {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .protocol {
            font-weight: 600;
            font-size: 0.95rem;
            cursor: text;
            border-bottom: 1px dashed transparent;
            transition: border-color 150ms ease;
        }
        .device-icon {
            --mdc-icon-size: 16px;
            color: var(--primary-color);
            flex-shrink: 0;
        }
        /* Remote drag handle (replaces the radio icon): blue, matches tab. */
        .remote-grip {
            --mdc-icon-size: 18px;
            color: var(--primary-color);
            cursor: grab;
            flex-shrink: 0;
            opacity: 0.85;
            transition: opacity 120ms ease;
        }
        .remote-grip:hover {
            opacity: 1;
        }
        .remote-grip:active {
            cursor: grabbing;
        }
        /* Signal drag handle: gray, same as the hits / time / frequency meta. */
        .signal-grip {
            --mdc-icon-size: 16px;
            color: var(--secondary-text-color);
            cursor: grab;
            flex-shrink: 0;
            opacity: 0.6;
            transition: opacity 120ms ease;
        }
        .signal-grip:hover {
            opacity: 1;
        }
        .signal-grip:active {
            cursor: grabbing;
        }
        /* SortableJS marks the element being dragged. */
        ha-card.sortable-ghost,
        .signal-row.sortable-ghost {
            opacity: 0.4;
        }
        .protocol:not(.locked):hover {
            border-bottom-color: var(--primary-color);
        }
        .protocol.locked {
            cursor: default;
        }
        .edit-icon {
            --mdc-icon-size: 14px;
            color: var(--secondary-text-color);
            cursor: pointer;
            opacity: 0.4;
            transition: opacity 150ms ease;
        }
        .device-header:hover .edit-icon {
            opacity: 0.8;
        }
        .edit-icon:hover {
            opacity: 1 !important;
            color: var(--primary-color);
        }
        /* Identical box to .promote-badge (now also uppercase, so no
           line-height hack needed) -- only the colour differs. */
        .status-badge.hair-device {
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            white-space: nowrap;
            flex-shrink: 0;
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
            border: 1px solid rgba(46, 125, 50, 0.3);
            margin-left: 4px;
        }
        .status-badge.promote-badge {
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            background: rgba(0, 151, 167, 0.15);
            color: #0097a7;
            border: 1px solid rgba(0, 151, 167, 0.35);
            margin-left: 4px;
            cursor: pointer;
            transition: background 150ms ease;
        }
        .status-badge.promote-badge:hover {
            background: rgba(0, 151, 167, 0.25);
        }
        .device-dismiss-btn {
            flex-shrink: 0;
        }
        .rename-input {
            font-weight: 600;
            font-size: 0.95rem;
            font-family: inherit;
            border: 1px solid var(--primary-color);
            border-radius: 4px;
            padding: 2px 6px;
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color);
            outline: none;
            width: 140px;
        }
        .address {
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            font-family: monospace;
        }
        .dismissed-badge {
            font-size: 0.7rem;
            background: var(--disabled-color, #999);
            color: white;
            padding: 1px 6px;
            border-radius: 4px;
            text-transform: uppercase;
        }
        .device-stats {
            display: inline-flex;
            align-items: center;
            gap: 12px;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
        }
        .stat strong {
            color: var(--primary-text-color);
        }
        .expand-icon {
            --mdc-icon-size: 24px;
            color: var(--secondary-text-color);
            flex-shrink: 0;
        }

        .expanded {
            border-top: 1px solid var(--divider-color);
            padding: 12px 16px 16px;
        }
        .signal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 8px;
        }
        .first-seen {
            color: var(--secondary-text-color);
            font-weight: 400;
        }
        .signal-list {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .signal-row {
            display: flex;
            align-items: center;
            padding: 6px 8px;
            /* Match the page background so the Sniffer signal rows blend
               with the panel backdrop instead of reading as highlighted
               peach strips, mirroring the device-detail command row
               treatment. Device-row hover (above) and action-btn hover
               (below) still use --secondary-background-color so hover
               feedback stays distinguishable. */
            background: var(--primary-background-color);
            border-radius: 4px;
            gap: 8px;
            flex-wrap: wrap;
        }
        /* Mobile layout fix.
           On narrow viewports the diamond pattern inside .signal-info
           wraps internally into a tall column, and flex/align-center
           floats the action buttons (Assign / Test / Trigger / Delete)
           into the vertical middle of the row with huge whitespace
           above and below. Switching to a 2-row grid keeps the
           diamonds + meta on the first row and stacks the action
           buttons below in their own band. Mirrors the bounded row
           height that the device-detail command rows already get via
           their fixed-column grid on every viewport. */
        @media (max-width: 768px) {
            .signal-row {
                display: grid;
                grid-template-columns: 1fr auto;
                align-items: start;
                gap: 6px 8px;
            }
            .signal-actions {
                grid-column: 1 / -1;
                justify-content: flex-start;
                flex-wrap: wrap;
            }
        }
        .signal-info {
            flex: 1;
            min-width: 0;
        }
        .signal-code {
            font-size: 0.82rem;
            word-break: break-all;
        }
        .signal-short-label {
            font-size: 0.82rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
        .diamonds {
            display: inline-flex;
            gap: 1px;
            flex-wrap: wrap;
            line-height: 1;
        }
        .diamond {
            font-size: 0.7rem;
        }
        .diamond.long {
            color: var(--primary-color);
        }
        .diamond.short {
            color: var(--warning-color, #ff9800);
        }
        .signal-meta {
            display: flex;
            gap: 12px;
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            white-space: nowrap;
        }
        .signal-actions {
            display: flex;
            gap: 4px;
            flex-shrink: 0;
        }

        /* Transient blue pulse on the Show Dismissed button when a
           signal arrives from a remote in the dismiss set. Reuses the
           same --primary-color blue users associate with "a signal just
           arrived", held ~3.8s so it sits about 1.3s longer than the
           hit-flash and stays discoverable. */
        .action-btn.dismiss-btn.dismiss-glow {
            animation: dismiss-pulse 3.8s ease-out;
            border-color: var(--primary-color);
        }
        @keyframes dismiss-pulse {
            0% { box-shadow: 0 0 0 0 rgba(33, 150, 243, 0.0); }
            12% { box-shadow: 0 0 10px 3px rgba(33, 150, 243, 0.55); }
            70% { box-shadow: 0 0 6px 2px rgba(33, 150, 243, 0.3); }
            100% { box-shadow: 0 0 0 0 rgba(33, 150, 243, 0.0); }
        }

        /* Persistent dot indicator anchored to the top-right of the
           Show Dismissed button. Stays visible from the first
           dismiss-activity event after panel mount until the user
           clicks the button (the natural click-through that owns
           restoring dismissed remotes). */
        .dismiss-dot {
            position: absolute;
            top: -3px;
            right: -3px;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--primary-color);
            box-shadow: 0 0 4px rgba(33, 150, 243, 0.55);
            pointer-events: none;
        }

        /* Latest signal: deep green fill (AA contrast with the white
           label) with a mint rim that previews the hit ring. Locked
           design: sniffer-hit-glow.md -- the earlier same-green halo
           read as a blob against the fill. */
        .action-btn.assign-btn.recent-latest {
            color: #fff;
            background: #2e7d32;
            border-color: #69f0ae;
        }
        .action-btn.assign-btn.recent-latest:hover {
            background: #1b5e20;
        }

        /* Previous signal: muted green outline Assign button */
        .action-btn.assign-btn.recent-previous {
            color: rgba(46, 125, 50, 0.6);
            border-color: rgba(46, 125, 50, 0.25);
            background: rgba(46, 125, 50, 0.06);
        }
        .action-btn.assign-btn.recent-previous:hover {
            background: rgba(46, 125, 50, 0.12);
        }

        /* Hit pulse: the mint rim blooms into a ring, brighter than
           the fill so the halo separates instead of blobbing. */
        .action-btn.assign-btn.glow {
            animation: assign-glow 1.4s ease-out;
        }
        @keyframes assign-glow {
            0% { box-shadow: 0 0 0 0 rgba(105, 240, 174, 0.9); }
            35% { box-shadow: 0 0 0 2px #69f0ae, 0 0 12px 5px rgba(105, 240, 174, 0.55); }
            100% { box-shadow: 0 0 0 0 rgba(105, 240, 174, 0); }
        }

        /* Hit count flash animation */
        .signal-meta .hit-flash {
            animation: hit-count-glow 1.2s ease-out;
        }
        @keyframes hit-count-glow {
            0% { color: #2e7d32; text-shadow: 0 0 6px rgba(46, 125, 50, 0.8); }
            100% { color: inherit; text-shadow: none; }
        }

        /* Collapsed stats flash on hit */
        .device-stats.stats-flash strong {
            color: var(--primary-color);
            transition: color 300ms ease;
        }
    `],e([pe({attribute:!1})],$s.prototype,"api",void 0),e([pe({attribute:!1})],$s.prototype,"hass",void 0),e([he()],$s.prototype,"_devices",void 0),e([he()],$s.prototype,"_hairDevices",void 0),e([he()],$s.prototype,"_loading",void 0),e([he()],$s.prototype,"_error",void 0),e([he()],$s.prototype,"_hasReceivers",void 0),e([he()],$s.prototype,"_showDismissed",void 0),e([he()],$s.prototype,"_expandedId",void 0),e([he()],$s.prototype,"_expandedDevice",void 0),e([he()],$s.prototype,"_flashIds",void 0),e([he()],$s.prototype,"_flashStats",void 0),e([he()],$s.prototype,"_recentSignalIds",void 0),e([he()],$s.prototype,"_glowSignalIds",void 0),e([he()],$s.prototype,"_hitFlashSignalIds",void 0),e([he()],$s.prototype,"_confirmClearAll",void 0),e([he()],$s.prototype,"_triggers",void 0),e([he()],$s.prototype,"_triggerDialog",void 0),e([he()],$s.prototype,"_triggerEditDialog",void 0),e([he()],$s.prototype,"_confirmDeleteTriggerId",void 0),e([he()],$s.prototype,"_triggerPopover",void 0),e([he()],$s.prototype,"_assignedPopover",void 0),e([he()],$s.prototype,"_receivers",void 0),e([he()],$s.prototype,"_editingDeviceId",void 0),e([he()],$s.prototype,"_editLabel",void 0),e([he()],$s.prototype,"_promoteTarget",void 0),e([he()],$s.prototype,"_assignSignal",void 0),e([he()],$s.prototype,"_deleteSignal",void 0),e([he()],$s.prototype,"_editSignal",void 0),e([he()],$s.prototype,"_testingSignalId",void 0),e([he()],$s.prototype,"_testResult",void 0),e([he()],$s.prototype,"_testDialog",void 0),e([he()],$s.prototype,"_testEmitters",void 0),e([he()],$s.prototype,"_dismissGlowActive",void 0),e([he()],$s.prototype,"_dismissDotVisible",void 0),e([he()],$s.prototype,"_remotesVersion",void 0),e([he()],$s.prototype,"_signalsVersion",void 0),$s=vs=e([me("ir-signal-monitor")],$s);let ws=class extends ne{constructor(){super(...arguments),this._name="",this._busy=!1,this._error=null,this._brands=[],this._selectedBrand="",this._selectedCodebook="",this._nameEdited=!1}connectedCallback(){super.connectedCallback(),this._loadBrands()}async _loadBrands(){try{this._brands=await this.api.getCodeBrands()}catch{this._brands=[]}}_brand(e){return this._brands.find(t=>t.brand===e)}_codebookLabel(e,t){const i=this._brand(e)?.codebooks.find(e=>e.id===t);return i?.label??""}_maybeAutofillName(){if(this._nameEdited)return;const e=this._brand(this._selectedBrand);if(!e||!this._selectedCodebook)return;const t=this._codebookLabel(this._selectedBrand,this._selectedCodebook);this._name=`${e.label} ${t}`.trim()}_onBrandChange(e){this._selectedBrand=e.target.value;const t=this._brand(this._selectedBrand);t&&1===t.codebooks.length?this._selectedCodebook=t.codebooks[0].id:this._selectedCodebook="",this._maybeAutofillName()}_onCodebookChange(e){this._selectedCodebook=e.target.value,this._maybeAutofillName()}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _create(){if(this._name.trim()){this._busy=!0,this._error=null;try{let e;e=this._selectedCodebook?(await this.api.importCodeRemote(this._selectedCodebook,this._name.trim())).device:await this.api.createRemote(this._name.trim()),this.dispatchEvent(new CustomEvent("remote-created",{detail:e,bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error=$e("common.name_required")}_onKeydown(e){"Enter"===e.key&&this._create()}render(){const e=this._brand(this._selectedBrand);return F`
            <ha-dialog
                open
                heading=${$e("createremote.heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?F`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <div class="field">
                    <label>${$e("common.name")}</label>
                    <input
                        type="text"
                        .value=${this._name}
                        placeholder=${$e("common.device_name_placeholder")}
                        required
                        autofocus
                        @input=${e=>{this._name=e.target.value,this._nameEdited=!0}}
                        @keydown=${this._onKeydown}
                    />
                </div>

                ${this._brands.length>0?F`
                          <div class="field">
                              <label>${$e("createremote.type")}</label>
                              <select
                                  .value=${this._selectedBrand}
                                  @change=${this._onBrandChange}
                              >
                                  <option value="">${$e("createremote.blank")}</option>
                                  <optgroup label=${$e("createremote.from_library")}>
                                      ${this._brands.map(e=>F`<option value=${e.brand}>
                                              ${e.label}
                                          </option>`)}
                                  </optgroup>
                              </select>
                          </div>

                          ${e?F`<div class="field">
                                    <label>${$e("createremote.model")}</label>
                                    <select
                                        .value=${this._selectedCodebook}
                                        @change=${this._onCodebookChange}
                                    >
                                        <option value="">
                                            ${$e("createremote.select_model")}
                                        </option>
                                        ${e.codebooks.map(e=>F`<option value=${e.id}>
                                                ${e.label}
                                                (${e.functions.length})
                                            </option>`)}
                                    </select>
                                </div>`:""}
                      `:""}

                <div class="dialog-actions">
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${$e("common.cancel")}
                    </button>
                    <button
                        class="action-btn create-btn"
                        @click=${this._create}
                        ?disabled=${this._busy}
                    >
                        ${this._busy?$e("common.creating"):$e("adddev.create")}
                    </button>
                </div>
            </ha-dialog>
        `}};ws.styles=[Fi,a`
        /* Tab-accent focus, overriding the shared primary-blue. */
        input[type="text"]:focus,
        select:focus {
            outline: none;
            border-color: #b87333;
        }
        ha-alert {
            display: block;
            margin: 8px 0;
        }
        .create-btn {
            background: #b87333;
            color: #fff;
            border-color: #b87333;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `],e([pe({attribute:!1})],ws.prototype,"api",void 0),e([he()],ws.prototype,"_name",void 0),e([he()],ws.prototype,"_busy",void 0),e([he()],ws.prototype,"_error",void 0),e([he()],ws.prototype,"_brands",void 0),e([he()],ws.prototype,"_selectedBrand",void 0),e([he()],ws.prototype,"_selectedCodebook",void 0),ws=e([me("ir-create-remote-dialog")],ws);const ks="M12.462,10.448c-0.639-0.639-1.678-0.639-2.317,0c-0.639,0.639-0.639,1.678,0,2.317l1.09,1.09c0.319,0.319,0.739,0.479,1.159,0.479c0.42,0,0.839-0.16,1.159-0.479c0-0,0-0,0-0c0.639-0.639,0.639-1.678,0-2.317L12.462,10.448z M12.763,13.066c-0.204,0.204-0.535,0.204-0.739,0l-1.09-1.09c-0.204-0.204-0.204-0.535,0-0.739c0.102-0.102,0.236-0.153,0.369-0.153c0.134,0,0.267,0.051,0.369,0.153l1.09,1.09C12.966,12.531,12.966,12.863,12.763,13.066z M23.998,6.609l-0.104-1.419c-0.02-0.276-0.24-0.496-0.516-0.516l-0.938-0.068l-0.068-0.938c-0.02-0.276-0.24-0.496-0.516-0.516l-0.938-0.068l-0.069-0.938c-0.02-0.276-0.24-0.496-0.516-0.516l-0.938-0.068l-0.069-0.938c-0.02-0.276-0.24-0.496-0.516-0.516l-1.419-0.103c-0.162-0.012-0.321,0.047-0.435,0.162l-1.993,1.993c-0,0.001-0.001,0.001-0.001,0.001c-0.097,0.097-0.191,0.197-0.282,0.298c-1.933,2.042-12.871,13.598-13.716,14.551c-0.722,0.814-0.712,1.983,0.023,2.717l0.341,0.341L0.539,20.852c-0.719,0.719-0.719,1.889,0,2.609c0.36,0.36,0.832,0.539,1.304,0.539c0.472,0,0.945-0.18,1.304-0.539l0.787-0.787l0.341,0.341c0.735,0.735,1.903,0.745,2.717,0.023c0.953-0.845,12.509-11.783,14.551-13.716c0.102-0.091,0.201-0.186,0.299-0.283c0.001-0.001,0.001-0.001,0.001-0.002l1.992-1.992C23.951,6.93,24.01,6.771,23.998,6.609z M20.61,4.179l0.684,0.05l0.05,0.684l-1.418,1.418l-0.733-0.734L20.61,4.179z M19.087,2.656l0.684,0.05l0.05,0.684L18.403,4.807L17.67,4.074L19.087,2.656z M17.564,1.133l0.684,0.05l0.05,0.684l-1.418,1.418l-0.733-0.733L17.564,1.133z M2.359,22.671c-0.284,0.284-0.746,0.284-1.03,0c-0.284-0.284-0.284-0.746,0-1.03l0.787-0.787l1.03,1.03L2.359,22.671z M6.253,22.202c-0.366,0.324-0.877,0.334-1.188,0.023l-0.735-0.735l-2.555-2.555c-0.311-0.311-0.301-0.822,0.023-1.188c0.633-0.715,7.3-7.769,11.189-11.88c-0.014,0.084-0.026,0.169-0.036,0.253c-0.179,1.482,0.239,2.815,1.176,3.752c0.937,0.937,2.27,1.355,3.752,1.176c0.084-0.01,0.169-0.022,0.253-0.036C14.022,14.901,6.968,21.568,6.253,22.202z M14.917,9.083c-0.69-0.69-0.994-1.694-0.857-2.829c0.123-1.019,0.585-2.03,1.315-2.897l0.717,0.717l-0.879,0.879c-0.218,0.218-0.218,0.571,0,0.789c0.218,0.218,0.571,0.218,0.789,0l0.879-0.879l0.734,0.734l-0.879,0.879c-0.218,0.218-0.218,0.571,0,0.789c0.218,0.218,0.571,0.218,0.789,0l0.879-0.879l0.734,0.734l-0.879,0.879c-0.218,0.218-0.218,0.571,0,0.789c0.218,0.218,0.571,0.218,0.789,0l0.879-0.879l0.717,0.717C18.756,10.213,16.277,10.443,14.917,9.083z M21.449,7.853l-0.734-0.734l1.418-1.418l0.684,0.05l0.05,0.684L21.449,7.853z",Cs="M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z";let Ss=class extends ne{constructor(){super(...arguments),this._devices=[],this._hairDevices=[],this._triggers=[],this._loading=!0,this._error=null,this._expandedId=null,this._expandedDevice=null,this._confirmClearAll=!1,this._deleteRemoteId=null,this._deleteRemoteLabel="",this._deleteRemoteCount=0,this._editingDeviceId=null,this._editLabel="",this._createRemoteOpen=!1,this._createSignalDeviceId=null,this._editSignal=null,this._promoteTarget=null,this._assignSignal=null,this._deleteSignal=null,this._triggerDialog=null,this._triggerEditDialog=null,this._triggerPopover=null,this._assignedPopover=null,this._receivers=[],this._unsubUpdated=null,this._confirmDeleteTriggerId=null,this._testDialog=null,this._testEmitters=[],this._testingSignalId=null,this._testResult=null,this._remotesVersion=0,this._signalsVersion=0,this._remotesSortable=null,this._signalsSortable=null,this._signalsSortableContainer=null,this._pendingRemotesSave=null,this._pendingSignalsSave=null,this._onDocClickForPopover=e=>{const t=e.composedPath(),i=this.shadowRoot?.querySelector("ir-trigger-popover"),s=this.shadowRoot?.querySelector("ir-assigned-popover");i&&t.includes(i)||s&&t.includes(s)||(this._closeTriggerPopover(),this._closeAssignedPopover())},this._onScrollForPopover=()=>{this._closeTriggerPopover(),this._closeAssignedPopover()}}connectedCallback(){super.connectedCallback(),this._load(),this._subscribeUpdated()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeUpdated(),this._removePopoverDismiss(),this._remotesSortable?.destroy(),this._remotesSortable=null,this._signalsSortable?.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null,null!==this._pendingRemotesSave&&clearTimeout(this._pendingRemotesSave),null!==this._pendingSignalsSave&&clearTimeout(this._pendingSignalsSave)}updated(e){if(super.updated(e),e.has("_editingDeviceId")&&this._editingDeviceId){const e=this.shadowRoot?.querySelector(".rename-input");e?.focus(),e?.select()}this._syncSortables()}_syncSortables(){const e=this.renderRoot.querySelector(".device-list");e&&!this._remotesSortable?this._attachRemotesSortable(e):!e&&this._remotesSortable&&(this._remotesSortable.destroy(),this._remotesSortable=null);const t=this.renderRoot.querySelector(".signal-list"),i=!!this._expandedDevice&&!this._expandedDevice.dismissed;!t||!i||this._signalsSortable&&this._signalsSortableContainer===t?t&&i||!this._signalsSortable||(this._signalsSortable.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null):(this._signalsSortable?.destroy(),this._attachSignalsSortable(t))}_attachRemotesSortable(e){this._remotesSortable=bi.create(e,{handle:".remote-grip",animation:150,ghostClass:"sortable-ghost",onEnd:t=>{const{oldIndex:i,newIndex:s}=t;if(void 0===i||void 0===s||i===s)return;const r=[...this._devices],[o]=r.splice(i,1);r.splice(s,0,o),this._devices=r,this._remotesSortable?.destroy(),this._remotesSortable=null,this._purgeChildren(e,"ha-card"),this._remotesVersion++,this._scheduleRemotesSave(r.map(e=>e.id))}})}_attachSignalsSortable(e){this._expandedDevice&&(this._signalsSortableContainer=e,this._signalsSortable=bi.create(e,{handle:".signal-grip",animation:150,ghostClass:"sortable-ghost",onEnd:t=>{const{oldIndex:i,newIndex:s}=t;if(void 0===i||void 0===s||i===s)return;const r=this._expandedDevice;if(!r)return;const o=[...r.signals],[a]=o.splice(i,1);o.splice(s,0,a),this._expandedDevice={...r,signals:o},this._signalsSortable?.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null,this._purgeChildren(e,".signal-row"),this._signalsVersion++,this._scheduleSignalsSave(r.id,o.map(e=>e.id))}}))}_purgeChildren(e,t){for(const i of Array.from(e.querySelectorAll(t)))i.remove()}_scheduleRemotesSave(e){null!==this._pendingRemotesSave&&clearTimeout(this._pendingRemotesSave),this._pendingRemotesSave=window.setTimeout(async()=>{this._pendingRemotesSave=null;try{await this.api.reorderUnknownDevices("manual",e)}catch(e){this._error=`Reorder failed: ${e.message}`,await this._load()}},500)}_scheduleSignalsSave(e,t){null!==this._pendingSignalsSave&&clearTimeout(this._pendingSignalsSave),this._pendingSignalsSave=window.setTimeout(async()=>{this._pendingSignalsSave=null;try{await this.api.reorderUnknownSignals(e,t)}catch(e){this._error=`Reorder failed: ${e.message}`,await this._refreshExpanded()}},500)}async _load(){this._loading=!0;try{const[e,t,i]=await Promise.all([this.api.getUnknownDevices({include_dismissed:!0,min_hits:0,source:"manual"}),this.api.listDevices(),this.api.listTriggers()]);this._devices=e,this._hairDevices=t,this._triggers=i,this._error=null,this.api.listReceivers().then(e=>{this._receivers=e}).catch(()=>{this._receivers=[]})}catch(e){this._error=`Failed to load: ${e.message}`}finally{this._loading=!1}}_matchesHairDevice(e){if(!e)return!1;const t=e.toLowerCase();return this._hairDevices.some(e=>e.name.toLowerCase()===t)}async _refreshExpanded(){if(this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{this._expandedId=null,this._expandedDevice=null}}openCreateRemote(){this._createRemoteOpen=!0}async _onRemoteCreated(e){this._createRemoteOpen=!1,await this._load(),this._expandedId=e.detail.id,await this._refreshExpanded()}_openCreateSignal(e,t){t.stopPropagation(),this._createSignalDeviceId=e}async _onSignalCreated(){this._createSignalDeviceId=null,await this._refreshExpanded(),await this._load()}_openEditSignal(e,t,i){i.stopPropagation(),this._editSignal={deviceId:e,signal:t}}async _onSignalEdited(){this._editSignal=null,await this._refreshExpanded(),await this._load()}_openDeleteRemote(e){this._deleteRemoteId=e.id,this._deleteRemoteLabel=e.label||"this remote",this._deleteRemoteCount=e.signals.length}async _confirmDeleteRemote(){const e=this._deleteRemoteId;if(this._deleteRemoteId=null,e)try{await this.api.deleteRemote(e),this._expandedId===e&&(this._expandedId=null,this._expandedDevice=null),await this._load()}catch(e){this._error=`Delete failed: ${e.message}`}}_onAliasChanged(e){const{id:t,alias:i}=e.detail;this._expandedDevice&&(this._expandedDevice={...this._expandedDevice,signals:this._expandedDevice.signals.map(e=>e.id===t?{...e,alias:i}:e)})}_startRename(e,t){t.stopPropagation(),this._editingDeviceId=e.id,this._editLabel=e.label??""}async _commitRename(e){const t=this._editLabel.trim();this._editingDeviceId=null;try{const i=await this.api.renameUnknown(e,t),s=this._devices.findIndex(t=>t.id===e);if(s>=0){const e=[...this._devices];e[s]={...e[s],label:i.label},this._devices=e}}catch(e){this._error=`Rename failed: ${e.message}`}}_onRenameKeydown(e,t){"Enter"===t.key?this._commitRename(e):"Escape"===t.key&&(this._editingDeviceId=null)}_promoteDevice(e,t){t.stopPropagation(),this._promoteTarget=e}async _onDevicePromoted(){this._promoteTarget=null,await this._load()}_openAssign(e,t,i){this._assignSignal={deviceId:e,signal:t,label:i??null}}_onAssignClick(e,t,i,s){if(!t.assigned_to?.length)return void this._openAssign(e,t,i);const r=s?.currentTarget,o=r?.getBoundingClientRect();this._assignedPopover={deviceId:e,signal:t,label:i??null,top:o?o.bottom+4:120,left:o?Math.max(8,o.right-220):120},this._installPopoverDismiss()}_closeAssignedPopover(){this._assignedPopover=null,this._removePopoverDismiss()}_onAssignedPopoverCreateNew(){const e=this._assignedPopover;this._closeAssignedPopover(),e&&this._openAssign(e.deviceId,e.signal,e.label)}_onAssignedPopoverOpen(e){const t=e.detail;this._closeAssignedPopover(),t&&this.dispatchEvent(new CustomEvent("navigate-device",{detail:t.device_id,bubbles:!0,composed:!0}))}async _onSignalAssigned(e){this._assignSignal=null,await this._load(),await this._refreshExpanded()}_openDelete(e,t){this._deleteSignal={deviceId:e,signal:t}}async _confirmDelete(){if(!this._deleteSignal)return;const{deviceId:e,signal:t}=this._deleteSignal;this._deleteSignal=null;try{await this.api.deleteSignal(e,t.id),await this._load(),await this._refreshExpanded()}catch(e){this._error=`Delete failed: ${e.message}`}}_openTestDialog(e){this._testDialog={signal:e}}async _sendTest(e){if(!this._testDialog)return;const{signal:t}=this._testDialog,i=e.detail.emitters;if(0!==i.length){this._testingSignalId=t.id,this._testResult=null,this._testDialog=null;try{const e=(await Promise.allSettled(i.map(e=>this.api.testSignal(t.id,e)))).filter(e=>"fulfilled"===e.status&&e.value.sent).length,s=i.length;this._testResult=e===s?1===s?$e("mirror.sent"):$e("mirror.sent_all_n",{sent:e,total:s}):0===e?$e("mirror.failed"):`Sent (${e}/${s})`}catch{this._testResult="Error"}setTimeout(()=>{this._testResult=null,this._testingSignalId=null},3e3)}}_hasTrigger(e){return this._triggers.some(t=>_s(t,e))}_triggerCountFor(e){return this._triggers.filter(t=>_s(t,e)).length}_openTriggerDialog(e,t,i){const s=this._triggers.filter(e=>_s(e,t));if(0===s.length)return void(this._triggerDialog={signal:t,deviceId:e});const r=i?.currentTarget,o=r?.getBoundingClientRect();this._triggerPopover={deviceId:e,signal:t,top:o?o.bottom+4:120,left:o?Math.max(8,o.right-220):120},this._installPopoverDismiss()}_closeTriggerPopover(){this._triggerPopover=null,this._removePopoverDismiss()}_onPopoverCreateNew(){const e=this._triggerPopover;this._closeTriggerPopover(),e&&(this._triggerDialog={signal:e.signal,deviceId:e.deviceId})}_onPopoverEditTrigger(e){const t=e.detail;this._closeTriggerPopover(),t&&(this._triggerEditDialog=t)}_installPopoverDismiss(){setTimeout(()=>{document.addEventListener("click",this._onDocClickForPopover,!0),window.addEventListener("scroll",this._onScrollForPopover,!0)},0)}_removePopoverDismiss(){document.removeEventListener("click",this._onDocClickForPopover,!0),window.removeEventListener("scroll",this._onScrollForPopover,!0)}async _subscribeUpdated(){try{this._unsubUpdated=await this.api.subscribeSignalUpdated(()=>{this._refreshAfterSignalUpdate()})}catch{}}async _unsubscribeUpdated(){this._unsubUpdated&&(await this._unsubUpdated(),this._unsubUpdated=null)}async _refreshAfterSignalUpdate(){try{this._triggers=await this.api.listTriggers()}catch{}if(this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{}}_closeTriggerDialog(){this._triggerDialog=null,this._triggerEditDialog=null}_requestDeleteTrigger(e){this._confirmDeleteTriggerId=e}async _doDeleteTrigger(){if(!this._confirmDeleteTriggerId)return;const e=this._confirmDeleteTriggerId;this._confirmDeleteTriggerId=null,this._triggerEditDialog=null;try{await this.api.deleteTrigger(e),this._triggers=await this.api.listTriggers()}catch{}}async _onTriggerSaved(){this._triggerDialog=null,this._triggerEditDialog=null;try{this._triggers=await this.api.listTriggers()}catch{}}async _toggleExpand(e){if(this._expandedId===e)return this._expandedId=null,void(this._expandedDevice=null);this._expandedId=e,await this._refreshExpanded()}async _doClearAll(){this._confirmClearAll=!1;try{await this.api.clearUnknowns("manual"),this._devices=[],this._expandedId=null,this._expandedDevice=null}catch(e){this._error=`Clear failed: ${e.message}`}}render(){const e=this._devices.length;return F`
            <div class="toolbar">
                <span class="title">
                    <ha-svg-icon .path=${ks}></ha-svg-icon>
                    ${$e("clips.title")}
                    ${this._loading?"":F`<span class="count"
                              >(${ke("sniffer.remotes",e)})</span
                          >`}
                </span>
                <div class="toolbar-actions">
                    <button
                        class="action-btn create-btn"
                        @click=${()=>this._createRemoteOpen=!0}
                    >
                        ${$e("clips.add_remote")}
                    </button>
                </div>
            </div>

            ${this._error?F`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

            ${this._loading?F`<div class="loading">${$e("common.loading_plain")}</div>`:0===e?F`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${ks}></ha-svg-icon>
                            <h3>${$e("clips.empty_title")}</h3>
                            <p>${$e("clips.empty_body")}</p>
                            <p class="hint">${$e("clips.empty_hint")}</p>
                        </ha-card>
                    `:F`
                        <div class="device-list">
                            ${He(this._remotesVersion,Ne(this._devices,e=>e.id,e=>this._renderDevice(e)))}
                        </div>
                    `}

            ${e>0?F`
                      <div class="clear-all-row">
                          <button
                              class="action-btn delete-btn"
                              title=${$e("clips.clear_all_title")}
                              @click=${()=>this._confirmClearAll=!0}
                          >
                              ${$e("sniffer.clear_all")}
                          </button>
                      </div>
                  `:""}

            ${this._renderDialogs()}
        `}_renderDevice(e){const t=this._expandedId===e.id;return F`
            <ha-card class="device clip-device">
                <div class="device-row" @click=${()=>this._toggleExpand(e.id)}>
                    <div class="device-info">
                        <div class="device-header">
                            ${this._editingDeviceId===e.id?F`<input
                                      class="rename-input"
                                      type="text"
                                      .value=${this._editLabel}
                                      @input=${e=>{this._editLabel=e.target.value}}
                                      @keydown=${t=>this._onRenameKeydown(e.id,t)}
                                      @blur=${()=>{this._commitRename(e.id)}}
                                      @click=${e=>e.stopPropagation()}
                                  />`:F`<ha-svg-icon
                                          class="remote-grip"
                                          .path=${Cs}
                                          title=${$e("devdetail.drag")}
                                          @click=${e=>e.stopPropagation()}
                                      ></ha-svg-icon>
                                      <span
                                          class="protocol"
                                          title=${$e("cmdrow.rename")}
                                          @click=${t=>this._startRename(e,t)}
                                          >${e.label??$e("clips.remote_fallback")}</span
                                      >`}
                            <span class="stat"
                                ><strong>${e.signal_count}</strong>
                                ${ke("sniffer.signal_word",e.signal_count)}</span
                            >
                            ${e.label&&this._matchesHairDevice(e.label)?F`<span
                                      class="status-badge hair-device"
                                      @click=${e=>e.stopPropagation()}
                                  >${$e("sniffer.hair_device")}</span>`:e.label?F`<span
                                          class="status-badge promote-badge"
                                          @click=${t=>this._promoteDevice(e,t)}
                                      >${$e("sniffer.promote")}</span>`:""}
                        </div>
                    </div>
                    <ha-svg-icon
                        class="expand-icon"
                        .path=${t?"M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z":"M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z"}
                    ></ha-svg-icon>
                </div>

                ${t&&this._expandedDevice?this._renderExpanded(this._expandedDevice):""}
            </ha-card>
        `}_renderExpanded(e){return F`
            <div class="expanded">
                <div class="signal-header">
                    <span>${$e("sniffer.signals_head",{count:e.signals.length})}</span>
                    <button
                        class="create-signal-btn"
                        title=${$e("clips.add_signal_title")}
                        @click=${t=>this._openCreateSignal(e.id,t)}
                    >
                        ${$e("clips.add_signal")}
                    </button>
                </div>
                ${0===e.signals.length?F`<div class="no-signals-row">
                          <span class="no-signals"
                              >${$e("clips.no_signals")}</span
                          >
                      </div>`:F`
                          <div class="signal-list">
                              ${He(this._signalsVersion,Ne(e.signals,e=>e.id,t=>this._renderSignal(e.id,t,e.label)))}
                          </div>
                      `}
                <div class="remote-footer">
                    <button
                        class="action-btn delete-btn"
                        title=${$e("clips.delete_remote_title")}
                        @click=${t=>{t.stopPropagation(),this._openDeleteRemote(e)}}
                    >${$e("clips.delete_remote")}</button>
                </div>
            </div>
        `}_renderSignal(e,t,i){const s=this._testingSignalId===t.id;return F`
            <div class="signal-row">
                <ha-svg-icon
                    class="signal-grip"
                    .path=${Cs}
                    title=${$e("devdetail.drag")}
                ></ha-svg-icon>
                <div class="signal-info">
                    <ir-signal-alias
                        .api=${this.api}
                        .deviceId=${e}
                        .signal=${t}
                        @alias-changed=${this._onAliasChanged}
                        @alias-error=${e=>this._error=e.detail}
                    ></ir-signal-alias>
                </div>
                <div class="signal-meta">
                    ${s&&this._testResult?F`<span class="test-result">${this._testResult}</span>`:F`<span>${Math.round(t.frequency/1e3)} kHz</span>`}
                </div>
                ${t.code?F`<button
                          title=${$e("cmdrow.edit_code")}
                          @click=${i=>this._openEditSignal(e,t,i)}
                          style="background:none;border:none;cursor:pointer;color:var(--secondary-text-color);padding:2px;display:inline-flex;align-items:center"
                      >
                          <ha-svg-icon
                              .path=${"M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"}
                              style="--mdc-icon-size:10px"
                          ></ha-svg-icon>
                      </button>`:""}
                <div class="signal-actions">
                    <button
                        class="action-btn assign-btn"
                        title=${t.assignment_count&&t.assigned_to?.length?1===t.assignment_count?`Assigned to ${t.assigned_to[0].device_name} / ${t.assigned_to[0].command_name}`:`Assigned to ${t.assignment_count} commands:\n- ${t.assigned_to.map(e=>`${e.device_name} / ${e.command_name}`).join("\n- ")}`:$e("mirror.assign_title")}
                        @click=${s=>{s.stopPropagation(),this._onAssignClick(e,t,i,s)}}
                    >${$e("assign.assign")}<ir-count-dot
                            color="green"
                            .count=${t.assignment_count??0}
                        ></ir-count-dot></button>
                    <button
                        class="action-btn test-btn"
                        ?disabled=${s}
                        title=${$e("clips.test_title")}
                        @click=${e=>{e.stopPropagation(),this._openTestDialog(t)}}
                    >${s?this._testResult??$e("mirror.sending"):$e("mirror.test")}</button>
                    <button
                        class="action-btn trigger-btn"
                        title=${this._hasTrigger(t)?$e("mirror.trigger_edit"):$e("sniffer.trigger_create")}
                        @click=${i=>{i.stopPropagation(),this._openTriggerDialog(e,t,i)}}
                    >${$e("cmdrow.trigger")}<ir-count-dot
                            color="yellow"
                            .count=${this._triggerCountFor(t)}
                        ></ir-count-dot></button>
                    <button
                        class="action-btn delete-btn"
                        @click=${i=>{i.stopPropagation(),this._openDelete(e,t)}}
                    >${$e("common.delete")}</button>
                </div>
            </div>
        `}_renderDialogs(){return F`
            ${this._createRemoteOpen?F`<ir-create-remote-dialog
                      .api=${this.api}
                      @remote-created=${this._onRemoteCreated}
                      @closed=${()=>this._createRemoteOpen=!1}
                  ></ir-create-remote-dialog>`:""}

            ${this._createSignalDeviceId?F`<ir-signal-editor
                      .api=${this.api}
                      .deviceId=${this._createSignalDeviceId}
                      @signal-created=${this._onSignalCreated}
                      @closed=${()=>this._createSignalDeviceId=null}
                  ></ir-signal-editor>`:""}

            ${this._editSignal?F`<ir-signal-editor
                      .api=${this.api}
                      .deviceId=${this._editSignal.deviceId}
                      .signalId=${this._editSignal.signal.id}
                      .initialPronto=${this._editSignal.signal.code??""}
                      .initialAlias=${this._editSignal.signal.alias??""}
                      .initialSendCount=${this._editSignal.signal.send_count??1}
                      .initialDitto=${this._editSignal.signal.repeat_count??1}
                      .initialObservedRepeatCount=${this._editSignal.signal.observed_repeat_count??0}
                      .hasTrigger=${this._hasTrigger(this._editSignal.signal)}
                      @signal-edited=${this._onSignalEdited}
                      @closed=${()=>this._editSignal=null}
                  ></ir-signal-editor>`:""}

            ${this._assignSignal?F`<ir-assign-signal-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .unknownDeviceId=${this._assignSignal.deviceId}
                      .signal=${this._assignSignal.signal}
                      .suggestedDeviceName=${this._assignSignal.label??""}
                      .initialMode=${"existing"}
                      @signal-assigned=${this._onSignalAssigned}
                      @closed=${()=>this._assignSignal=null}
                  ></ir-assign-signal-dialog>`:""}

            ${this._promoteTarget?F`<ir-promote-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .suggestedName=${this._promoteTarget.label??""}
                      @device-created=${this._onDevicePromoted}
                      @closed=${()=>this._promoteTarget=null}
                  ></ir-promote-dialog>`:""}

            ${this._deleteSignal?F`<ir-confirm-dialog
                      title=${$e("sniffer.del_signal_title")}
                      message=${$e("sniffer.del_signal_msg")}
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._confirmDelete}
                      @closed=${()=>this._deleteSignal=null}
                  ></ir-confirm-dialog>`:""}

            ${this._confirmClearAll?F`<ir-confirm-dialog
                      title=${$e("clips.clear_all_confirm_title")}
                      message=${$e("clips.clear_all_confirm_msg")}
                      confirmLabel=${$e("sniffer.clear_all")}
                      .destructive=${!0}
                      @confirmed=${this._doClearAll}
                      @closed=${()=>this._confirmClearAll=!1}
                  ></ir-confirm-dialog>`:""}

            ${this._deleteRemoteId?F`<ir-confirm-dialog
                      title=${$e("clips.del_remote_confirm_title")}
                      message=${this._deleteRemoteCount>0?ke("clips.del_remote_msg_n",this._deleteRemoteCount,{name:this._deleteRemoteLabel??""}):$e("clips.del_remote_msg",{name:this._deleteRemoteLabel??""})}
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._confirmDeleteRemote}
                      @closed=${()=>this._deleteRemoteId=null}
                  ></ir-confirm-dialog>`:""}

            ${this._triggerPopover?F`<ir-trigger-popover
                      .triggers=${this._triggers.filter(e=>_s(e,this._triggerPopover.signal))}
                      .receivers=${this._receivers}
                      .top=${this._triggerPopover.top}
                      .left=${this._triggerPopover.left}
                      @create-new=${this._onPopoverCreateNew}
                      @edit-trigger=${this._onPopoverEditTrigger}
                  ></ir-trigger-popover>`:""}

            ${this._assignedPopover?F`<ir-assigned-popover
                      .assignments=${this._assignedPopover.signal.assigned_to??[]}
                      .top=${this._assignedPopover.top}
                      .left=${this._assignedPopover.left}
                      @create-new=${this._onAssignedPopoverCreateNew}
                      @open-assignment=${this._onAssignedPopoverOpen}
                  ></ir-assigned-popover>`:""}

            ${this._triggerDialog?F`<ir-trigger-dialog
                      .api=${this.api}
                      .signalFingerprint=${this._triggerDialog.signal.fingerprint}
                      .byteHash=${this._triggerDialog.signal.byte_hash??null}
                      .decodedFingerprint=${this._triggerDialog.signal.decoded_fingerprint??null}
                      .protocol=${this._triggerDialog.signal.protocol}
                      .code=${this._triggerDialog.signal.code}
                      .slPattern=${this._triggerDialog.signal.sl_pattern??null}
                      .alias=${this._triggerDialog.signal.alias||null}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                  ></ir-trigger-dialog>`:""}

            ${this._triggerEditDialog?F`<ir-trigger-dialog
                      .api=${this.api}
                      .trigger=${this._triggerEditDialog}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                      @trigger-delete=${e=>this._requestDeleteTrigger(e.detail.triggerId)}
                  ></ir-trigger-dialog>`:""}

            ${this._confirmDeleteTriggerId?F`<ir-confirm-dialog
                      title=${$e("mirror.del_trigger_title")}
                      message=${$e("devdetail.del_trigger_msg")}
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._doDeleteTrigger}
                      @closed=${()=>this._confirmDeleteTriggerId=null}
                  ></ir-confirm-dialog>`:""}

            ${this._testDialog?F`<ir-test-emitter-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .value=${this._testEmitters}
                      @emitters-changed=${e=>this._testEmitters=e.detail.value}
                      @send=${this._sendTest}
                      @closed=${()=>this._testDialog=null}
                  ></ir-test-emitter-dialog>`:""}
        `}};Ss.styles=[Vi,a`
        :host {
            display: block;
        }
        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--primary-text-color);
        }
        .title ha-svg-icon {
            --mdc-icon-size: 24px;
            color: #b87333;
        }
        .count {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
        }
        .toolbar-actions {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        /* Header "+ Create" -- sized to match the Hide Dismissed (action-btn)
           button beside it: same padding/font, copper colors. */
        /* Toolbar "+ Add Remote": shared chip anatomy, copper accent. */
        .action-btn.create-btn {
            color: #b87333;
            border-color: #b87333;
        }
        .action-btn.create-btn:hover:not(:disabled) {
            background: rgba(184, 115, 51, 0.08);
        }
        /* Card-internal "+ Add Signal": borderless copper text action
           (no chip, no stroke -- owner ruling), one pixel up from its
           old size, font color matching the Add Remote accent. */
        .create-signal-btn {
            border: none;
            background: none;
            padding: 0;
            font-size: 10px;
            font-weight: 500;
            font-family: inherit;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            color: #b87333;
            cursor: pointer;
        }
        .create-signal-btn:hover:not(:disabled) {
            background: none;
            text-decoration: underline;
        }

        .clear-all-row {
            display: flex;
            justify-content: flex-end;
            margin-top: 16px;
        }
        /* Show Dismissed stacked above Clear All, both right-aligned. */
        .bottom-bar {
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 8px;
            margin-top: 16px;
        }
        .loading,
        .empty {
            padding: 48px 24px;
            text-align: center;
            color: var(--secondary-text-color);
        }
        .empty-icon {
            --mdc-icon-size: 48px;
            color: #b87333;
            opacity: 0.5;
            margin-bottom: 16px;
        }
        .empty h3 {
            color: var(--primary-text-color);
            margin: 8px 0;
        }
        .hint {
            font-size: 0.85rem;
            font-style: italic;
        }

        .device-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .device.clip-device {
            border: 1px solid rgba(184, 115, 51, 0.3);
            /* Clip the row's rectangular hover highlight to the card's
               rounded corners so its square corners do not poke out over
               the border stroke. */
            overflow: hidden;
        }
        .device.dismissed {
            opacity: 0.6;
        }
        .device-row {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            cursor: pointer;
            gap: 12px;
        }
        .device-row:hover {
            background: var(--secondary-background-color);
        }
        .device-info {
            flex: 1;
            min-width: 0;
        }
        .device-header {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .clip-icon {
            --mdc-icon-size: 14px;
            color: #b87333;
        }
        /* Remote drag handle (replaces the paperclip): copper, matches tab. */
        .remote-grip {
            --mdc-icon-size: 18px;
            color: #b87333;
            cursor: grab;
            flex-shrink: 0;
            opacity: 0.85;
            transition: opacity 120ms ease;
        }
        .remote-grip:hover {
            opacity: 1;
        }
        .remote-grip:active {
            cursor: grabbing;
        }
        /* Signal drag handle: gray, same as the hits / time / frequency meta. */
        .signal-grip {
            --mdc-icon-size: 16px;
            color: var(--secondary-text-color);
            cursor: grab;
            flex-shrink: 0;
            opacity: 0.6;
            transition: opacity 120ms ease;
        }
        .signal-grip:hover {
            opacity: 1;
        }
        .signal-grip:active {
            cursor: grabbing;
        }
        /* SortableJS marks the element being dragged. */
        ha-card.sortable-ghost,
        .signal-row.sortable-ghost {
            opacity: 0.4;
        }
        .protocol {
            font-weight: 600;
            font-size: 0.95rem;
            cursor: text;
            border-bottom: 1px dashed transparent;
            transition: border-color 150ms ease;
        }
        .protocol:not(.locked):hover {
            border-bottom-color: #b87333;
        }
        .protocol.locked {
            cursor: default;
        }
        .rename-input {
            font-weight: 600;
            font-size: 0.95rem;
            font-family: inherit;
            border: 1px solid #b87333;
            border-radius: 4px;
            padding: 2px 6px;
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color);
            outline: none;
            width: 160px;
        }
        .dismissed-badge {
            font-size: 0.7rem;
            background: var(--disabled-color, #999);
            color: white;
            padding: 1px 6px;
            border-radius: 4px;
            text-transform: uppercase;
        }
        .stat {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
        }
        .stat strong {
            color: var(--primary-text-color);
        }
        .status-badge.hair-device {
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            white-space: nowrap;
            flex-shrink: 0;
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
            border: 1px solid rgba(46, 125, 50, 0.3);
        }
        .status-badge.promote-badge {
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            background: rgba(0, 151, 167, 0.15);
            color: #0097a7;
            border: 1px solid rgba(0, 151, 167, 0.35);
            cursor: pointer;
            transition: background 150ms ease;
        }
        .status-badge.promote-badge:hover {
            background: rgba(0, 151, 167, 0.25);
        }
        .device-dismiss-btn {
            flex-shrink: 0;
        }
        .expand-icon {
            --mdc-icon-size: 24px;
            color: var(--secondary-text-color);
            flex-shrink: 0;
        }

        .expanded {
            border-top: 1px solid var(--divider-color);
            padding: 12px 16px 16px;
        }
        /* "+ Create" sits immediately right of the "Signals (N)" label,
           left-aligned, rather than pushed to the far right. */
        .signal-header {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 8px;
        }
        .no-signals-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            padding: 6px 8px;
        }
        .no-signals {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
        /* Persistent "Delete remote" footer: a row below the signal list,
           right-justified so its button lines up with the per-signal Delete
           buttons (which sit 8px in from the row edge). Same button size as
           every other action button. */
        .remote-footer {
            display: flex;
            justify-content: flex-end;
            margin-top: 10px;
            padding-right: 8px;
        }
        .signal-list {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .signal-row {
            display: flex;
            align-items: center;
            padding: 6px 8px;
            background: var(--primary-background-color);
            border-radius: 4px;
            gap: 8px;
            flex-wrap: wrap;
        }
        @media (max-width: 768px) {
            .signal-row {
                display: grid;
                grid-template-columns: 1fr auto;
                align-items: start;
                gap: 6px 8px;
            }
            .signal-actions {
                grid-column: 1 / -1;
                justify-content: flex-start;
                flex-wrap: wrap;
            }
        }
        .signal-info {
            flex: 1;
            min-width: 0;
        }
        .signal-meta {
            display: flex;
            gap: 12px;
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            white-space: nowrap;
        }
        .test-result {
            color: #2e7d32;
            font-weight: 500;
        }
        .signal-actions {
            display: flex;
            gap: 4px;
            flex-shrink: 0;
        }
    `],e([pe({attribute:!1})],Ss.prototype,"api",void 0),e([pe({attribute:!1})],Ss.prototype,"hass",void 0),e([he()],Ss.prototype,"_devices",void 0),e([he()],Ss.prototype,"_hairDevices",void 0),e([he()],Ss.prototype,"_triggers",void 0),e([he()],Ss.prototype,"_loading",void 0),e([he()],Ss.prototype,"_error",void 0),e([he()],Ss.prototype,"_expandedId",void 0),e([he()],Ss.prototype,"_expandedDevice",void 0),e([he()],Ss.prototype,"_confirmClearAll",void 0),e([he()],Ss.prototype,"_deleteRemoteId",void 0),e([he()],Ss.prototype,"_deleteRemoteLabel",void 0),e([he()],Ss.prototype,"_deleteRemoteCount",void 0),e([he()],Ss.prototype,"_editingDeviceId",void 0),e([he()],Ss.prototype,"_editLabel",void 0),e([he()],Ss.prototype,"_createRemoteOpen",void 0),e([he()],Ss.prototype,"_createSignalDeviceId",void 0),e([he()],Ss.prototype,"_editSignal",void 0),e([he()],Ss.prototype,"_promoteTarget",void 0),e([he()],Ss.prototype,"_assignSignal",void 0),e([he()],Ss.prototype,"_deleteSignal",void 0),e([he()],Ss.prototype,"_triggerDialog",void 0),e([he()],Ss.prototype,"_triggerEditDialog",void 0),e([he()],Ss.prototype,"_triggerPopover",void 0),e([he()],Ss.prototype,"_assignedPopover",void 0),e([he()],Ss.prototype,"_receivers",void 0),e([he()],Ss.prototype,"_confirmDeleteTriggerId",void 0),e([he()],Ss.prototype,"_testDialog",void 0),e([he()],Ss.prototype,"_testEmitters",void 0),e([he()],Ss.prototype,"_testingSignalId",void 0),e([he()],Ss.prototype,"_testResult",void 0),e([he()],Ss.prototype,"_remotesVersion",void 0),e([he()],Ss.prototype,"_signalsVersion",void 0),Ss=e([me("ir-clips")],Ss);let Ds=class extends ne{constructor(){super(...arguments),this.pendingEntity="",this._candidates=[],this._entityId="",this._appliance="",this._name="",this._busy=!1,this._loading=!0,this._error=null,this._nameEdited=!1}connectedCallback(){super.connectedCallback(),this._loadVendors()}async _loadVendors(){this._loading=!0;try{const{vendors:e}=await this.api.listPluckVendors();this._candidates=this._flatten(e);const t=this._candidates.find(e=>e.entityId===this.pendingEntity)??(1===this._candidates.length?this._candidates[0]:void 0);t&&(this._entityId=t.entityId,this._autofillName())}catch(e){this._error=e.message,this._candidates=[]}finally{this._loading=!1}}_flatten(e){const t=[];for(const i of e)for(const e of i.blasters)t.push({integration:i.integration,entityId:e.entity_id,vendorName:i.name,blasterName:e.name,applianceLabel:i.appliance_label||"Appliance",applianceHelp:i.appliance_help||""});return t}get _selected(){return this._candidates.find(e=>e.entityId===this._entityId)}_autofillName(){if(this._nameEdited)return;const e=this._selected;if(!e)return;const t=this._appliance.trim();this._name=(t?`${e.blasterName}: ${t}`:e.blasterName).trim()}_onVendorChange(e){this._entityId=e.target.value,this._autofillName()}_onApplianceInput(e){this._appliance=e.target.value,this._autofillName()}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _create(){const e=this._selected;if(e)if(this._appliance.trim())if(this._name.trim()){this._busy=!0,this._error=null;try{const t=await this.api.createPluckedBlaster({vendor_entity_id:e.entityId,appliance:this._appliance.trim(),name:this._name.trim()});this.dispatchEvent(new CustomEvent("blaster-created",{detail:t,bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error=$e("common.name_required");else this._error=$e("pluckdlg.appliance_required");else this._error=$e("pluckdlg.blaster_required")}render(){const e=this._selected;return F`
            <ha-dialog
                open
                heading=${$e("pluckdlg.add_heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?F`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                ${this._loading?F`<div class="muted">${$e("pluckdlg.loading_blasters")}</div>`:0===this._candidates.length?F`<div class="muted">
                            ${$e("pluckdlg.no_blasters")}
                        </div>`:F`
                            <div class="field">
                                <label>${$e("pluckdlg.pluck_from")}</label>
                                <select
                                    .value=${this._entityId}
                                    @change=${this._onVendorChange}
                                >
                                    <option value="">${$e("pluckdlg.select_blaster")}</option>
                                    ${this._candidates.map(e=>F`<option
                                            value=${e.entityId}
                                        >
                                            ${e.vendorName}: ${e.blasterName}
                                        </option>`)}
                                </select>
                            </div>

                            <div class="field">
                                <label>${e?.applianceLabel??$e("pluckdlg.appliance")}</label>
                                <input
                                    type="text"
                                    .value=${this._appliance}
                                    placeholder=${$e("pluckdlg.appliance_placeholder")}
                                    required
                                    @input=${this._onApplianceInput}
                                />
                                ${e?.applianceHelp?F`<div class="help">
                                          ${e.applianceHelp}
                                      </div>`:""}
                            </div>

                            <div class="field">
                                <label>${$e("common.name")}</label>
                                <input
                                    type="text"
                                    .value=${this._name}
                                    placeholder=${$e("pluckdlg.name_placeholder")}
                                    @input=${e=>{this._name=e.target.value,this._nameEdited=!0}}
                                />
                            </div>
                        `}

                <div class="dialog-actions">
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        ${$e("common.cancel")}
                    </button>
                    <button
                        class="action-btn create-btn"
                        @click=${this._create}
                        ?disabled=${this._busy||0===this._candidates.length}
                    >
                        ${this._busy?$e("common.creating"):$e("common.create")}
                    </button>
                </div>
            </ha-dialog>
        `}};Ds.styles=[Fi,a`
        .help {
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            margin-top: 4px;
        }
        .muted {
            color: var(--secondary-text-color);
            font-size: 0.9rem;
            margin: 12px 0;
        }
        /* Tab-accent focus, overriding the shared primary-blue. */
        input[type="text"]:focus,
        select:focus {
            outline: none;
            border-color: #455a64;
        }
        ha-alert {
            display: block;
            margin: 8px 0;
        }
        .create-btn {
            background: #455a64;
            color: #fff;
            border-color: #455a64;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `],e([pe({attribute:!1})],Ds.prototype,"api",void 0),e([pe()],Ds.prototype,"pendingEntity",void 0),e([he()],Ds.prototype,"_candidates",void 0),e([he()],Ds.prototype,"_entityId",void 0),e([he()],Ds.prototype,"_appliance",void 0),e([he()],Ds.prototype,"_name",void 0),e([he()],Ds.prototype,"_busy",void 0),e([he()],Ds.prototype,"_loading",void 0),e([he()],Ds.prototype,"_error",void 0),Ds=e([me("ir-pluck-add-remote-dialog")],Ds);let As=class extends ne{constructor(){super(...arguments),this.integration="",this._commandName="",this._busy=!1,this._creating=!1,this._error=null,this._captures=null,this._aliases=[],this._validations=[]}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _pluck(){const e=this._commandName.trim();if(e){this._busy=!0,this._error=null;try{const t=await this.api.runPluck({integration:this.integration,vendor_entity_id:this.blaster.vendor_entity_id??"",appliance:this.blaster.appliance??"",command_name:e});t.error?this._error=t.message??$e("pluckdlg.pluck_failed"):t.signals&&t.signals.length>0?(this._captures=t.signals,this._aliases=t.signals.map(e=>e.suggested_alias),this._validations=await Promise.all(t.signals.map(e=>this.api.validatePronto(e.code??"").catch(()=>null)))):this._error=$e("pluckdlg.no_response")}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error=$e("assign.command_required")}_removeCapture(e){this._captures&&(this._captures=this._captures.filter((t,i)=>i!==e),this._aliases=this._aliases.filter((t,i)=>i!==e),this._validations=this._validations.filter((t,i)=>i!==e),0===this._captures.length&&(this._captures=null))}async _create(){if(this._captures&&0!==this._captures.length){this._creating=!0,this._error=null;try{const e=[];for(let t=0;t<this._captures.length;t++){const i=this._captures[t],s=await this.api.createPluckedSignal({device_id:this.blaster.id,pronto:i.code??"",command_name:i.plucked_command_name,alias:this._aliases[t].trim()});e.push(s)}this.dispatchEvent(new CustomEvent("signals-created",{detail:e,bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._creating=!1}}}_renderValid(e,t){const i=this._validations[t]??null,s=i?.recognized_protocol??e.decoded_protocol??null,r=null!=i?.frequency_khz?i.frequency_khz.toFixed(1):(e.frequency/1e3).toFixed(1),o=i?.burst_pair_count??null;return F`
            <div class="valid-box">
                <div class="valid-head">
                    <ha-svg-icon .path=${"M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z"}></ha-svg-icon>
                    ${s?$e("pluckdlg.recognized_as",{protocol:s}):$e("pluckdlg.valid_pronto")}
                </div>
                <div class="valid-sub">
                    ${r} kHz${null!=o?` · ${o} burst pairs`:""}
                </div>
            </div>
        `}_renderError(){return this._error?F`
            <div class="pluck-error">
                <ha-svg-icon .path=${"M11,15H13V17H11V15M11,7H13V13H11V7M12,2C6.47,2 2,6.5 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20Z"}></ha-svg-icon>
                <span>${this._error}</span>
            </div>
        `:""}_renderCommandState(){return F`
            <div class="field">
                <label>${$e("assign.command_name")}</label>
                <input
                    type="text"
                    .value=${this._commandName}
                    placeholder=${$e("pluckdlg.command_placeholder")}
                    autofocus
                    @input=${e=>this._commandName=e.target.value}
                    @keydown=${e=>{"Enter"===e.key&&this._pluck()}}
                />
                <div class="help">
                    ${$e("pluckdlg.command_help")}
                </div>
            </div>
            ${this._renderError()}
            <div class="dialog-actions">
                <button
                    class="action-btn cancel-btn"
                    @click=${this._close}
                    ?disabled=${this._busy}
                >
                    ${$e("common.cancel")}
                </button>
                <button
                    class="action-btn pluck-btn"
                    @click=${this._pluck}
                    ?disabled=${this._busy}
                >
                    ${this._busy?$e("pluckdlg.plucking"):$e("pluckdlg.pluck")}
                </button>
            </div>
        `}_renderCaptures(e){const t=e.length>1;return F`
            ${this._renderError()}
            <div class="captured-label">
                ${$e("pluckdlg.captured")} ${t?`(${e.length})`:""}
            </div>
            ${e.map((e,i)=>F`
                    <div class="capture">
                        ${t?F`<button
                                  class="remove-btn"
                                  title=${$e("pluckdlg.remove_capture")}
                                  @click=${()=>this._removeCapture(i)}
                              >
                                  &times;
                              </button>`:""}
                        <div class="pronto">${e.code}</div>
                        ${this._renderValid(e,i)}
                        <div class="field">
                            <label>${$e("pluckdlg.alias")}</label>
                            <input
                                type="text"
                                .value=${this._aliases[i]??""}
                                @input=${e=>{const t=e.target.value,s=[...this._aliases];s[i]=t,this._aliases=s}}
                            />
                        </div>
                    </div>
                `)}
            <div class="dialog-actions">
                <button
                    class="action-btn cancel-btn"
                    @click=${this._close}
                    ?disabled=${this._creating}
                >
                    ${$e("common.cancel")}
                </button>
                <button
                    class="action-btn create-btn"
                    @click=${this._create}
                    ?disabled=${this._creating}
                >
                    ${this._creating?$e("common.saving"):$e("common.create")}
                </button>
            </div>
        `}render(){return F`
            <ha-dialog
                open
                heading=${$e("pluckdlg.signal_heading")}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._captures?this._renderCaptures(this._captures):this._renderCommandState()}
            </ha-dialog>
        `}};As.styles=[Fi,a`
        .help {
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            margin-top: 4px;
        }
        /* Tab-accent focus, overriding the shared primary-blue. */
        input[type="text"]:focus {
            outline: none;
            border-color: #455a64;
        }
        .pluck-error {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 12px 0;
            padding: 8px 12px;
            border-radius: 6px;
            background: rgba(255, 152, 0, 0.1);
            border-left: 3px solid var(--warning-color, #ff9800);
            color: var(--primary-text-color);
            font-size: 0.85rem;
            line-height: 1.3;
        }
        .pluck-error ha-svg-icon {
            --mdc-icon-size: 18px;
            color: var(--warning-color, #ff9800);
            flex-shrink: 0;
        }
        .captured-label {
            font-size: 0.8rem;
            font-weight: 600;
            color: var(--secondary-text-color);
            margin: 12px 0 6px;
        }
        .capture {
            position: relative;
            margin-bottom: 12px;
        }
        .capture + .capture {
            border-top: 1px solid var(--divider-color);
            padding-top: 12px;
        }
        .remove-btn {
            position: absolute;
            top: 6px;
            right: 6px;
            border: none;
            background: none;
            color: var(--secondary-text-color);
            font-size: 1.1rem;
            line-height: 1;
            cursor: pointer;
            padding: 2px 6px;
        }
        .remove-btn:hover {
            color: var(--error-color, #c62828);
        }
        .pronto {
            font-family: var(--code-font-family, monospace);
            font-size: 0.72rem;
            color: var(--primary-text-color);
            background: var(--secondary-background-color);
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 8px;
            max-height: 96px;
            overflow: auto;
            word-break: break-all;
        }
        .valid-box {
            margin-top: 8px;
            background: var(--secondary-background-color);
            border-radius: 6px;
            padding: 8px 10px;
        }
        .valid-head {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.82rem;
            font-weight: 600;
            color: #2e7d32;
        }
        .valid-head ha-svg-icon {
            --mdc-icon-size: 16px;
        }
        .valid-sub {
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            margin-top: 4px;
        }
        .pluck-btn,
        .create-btn {
            background: #455a64;
            color: #fff;
            border-color: #455a64;
        }
        .pluck-btn:hover:not(:disabled),
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `],e([pe({attribute:!1})],As.prototype,"api",void 0),e([pe({attribute:!1})],As.prototype,"blaster",void 0),e([pe()],As.prototype,"integration",void 0),e([he()],As.prototype,"_commandName",void 0),e([he()],As.prototype,"_busy",void 0),e([he()],As.prototype,"_creating",void 0),e([he()],As.prototype,"_error",void 0),e([he()],As.prototype,"_captures",void 0),e([he()],As.prototype,"_aliases",void 0),e([he()],As.prototype,"_validations",void 0),As=e([me("ir-pluck-signal-dialog")],As);const Ts="M0.861,24c-0.22,0-0.441-0.084-0.609-0.252c-0.336-0.336-0.336-0.882,0-1.218l1.563-1.563c1.648-1.649,3.474-4.166,5.588-7.082c2.984-4.116,6.367-8.781,10.695-13.109c0.081-0.081,0.178-0.145,0.284-0.189l1.283-0.523c0.441-0.18,0.943,0.032,1.123,0.472l-0.472,1.123L19.194,2.116c-4.175,4.199-7.478,8.755-10.397,12.78c-0.275,0.379-0.545,0.752-0.811,1.117c0.365-0.266,0.738-0.536,1.117-0.811C13.128,12.284,17.685,8.98,21.884,4.806l0.457-1.121L23.464,3.212c0.44,0.18,0.652,0.682,0.472,1.123l-0.523,1.283c-0.043,0.106-0.107,0.203-0.188,0.284c-4.329,4.329-8.994,7.711-13.109,10.695c-2.915,2.114-5.433,3.939-7.082,5.588l-1.563,1.563C1.302,23.916,1.082,24,0.861,24z",Es="M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z";let Is=class extends ne{constructor(){super(...arguments),this.pendingEntity="",this._devices=[],this._hairDevices=[],this._triggers=[],this._loading=!0,this._error=null,this._expandedId=null,this._expandedDevice=null,this._confirmClearAll=!1,this._deleteRemoteId=null,this._deleteRemoteLabel="",this._deleteRemoteCount=0,this._vendorIntegration={},this._editingDeviceId=null,this._editLabel="",this._createRemoteOpen=!1,this._promoteTarget=null,this._pluckDialog=null,this._editSignal=null,this._assignSignal=null,this._deleteSignal=null,this._triggerDialog=null,this._triggerEditDialog=null,this._triggerPopover=null,this._assignedPopover=null,this._receivers=[],this._unsubUpdated=null,this._confirmDeleteTriggerId=null,this._testDialog=null,this._testEmitters=[],this._testingSignalId=null,this._testResult=null,this._remotesVersion=0,this._signalsVersion=0,this._remotesSortable=null,this._signalsSortable=null,this._signalsSortableContainer=null,this._pendingRemotesSave=null,this._pendingSignalsSave=null,this._onDocClickForPopover=e=>{const t=e.composedPath(),i=this.shadowRoot?.querySelector("ir-trigger-popover"),s=this.shadowRoot?.querySelector("ir-assigned-popover");i&&t.includes(i)||s&&t.includes(s)||(this._closeTriggerPopover(),this._closeAssignedPopover())},this._onScrollForPopover=()=>{this._closeTriggerPopover(),this._closeAssignedPopover()}}connectedCallback(){super.connectedCallback(),this._load(),this._subscribeUpdated()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeUpdated(),this._removePopoverDismiss(),this._remotesSortable?.destroy(),this._remotesSortable=null,this._signalsSortable?.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null,null!==this._pendingRemotesSave&&clearTimeout(this._pendingRemotesSave),null!==this._pendingSignalsSave&&clearTimeout(this._pendingSignalsSave)}updated(e){if(super.updated(e),e.has("_editingDeviceId")&&this._editingDeviceId){const e=this.shadowRoot?.querySelector(".rename-input");e?.focus(),e?.select()}this._syncSortables()}_syncSortables(){const e=this.renderRoot.querySelector(".device-list");e&&!this._remotesSortable?this._attachRemotesSortable(e):!e&&this._remotesSortable&&(this._remotesSortable.destroy(),this._remotesSortable=null);const t=this.renderRoot.querySelector(".signal-list"),i=!!this._expandedDevice;!t||!i||this._signalsSortable&&this._signalsSortableContainer===t?t&&i||!this._signalsSortable||(this._signalsSortable.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null):(this._signalsSortable?.destroy(),this._attachSignalsSortable(t))}_attachRemotesSortable(e){this._remotesSortable=bi.create(e,{handle:".remote-grip",animation:150,ghostClass:"sortable-ghost",onEnd:t=>{const{oldIndex:i,newIndex:s}=t;if(void 0===i||void 0===s||i===s)return;const r=[...this._devices],[o]=r.splice(i,1);r.splice(s,0,o),this._devices=r,this._remotesSortable?.destroy(),this._remotesSortable=null,this._purgeChildren(e,"ha-card"),this._remotesVersion++,this._scheduleRemotesSave(r.map(e=>e.id))}})}_attachSignalsSortable(e){this._expandedDevice&&(this._signalsSortableContainer=e,this._signalsSortable=bi.create(e,{handle:".signal-grip",animation:150,ghostClass:"sortable-ghost",onEnd:t=>{const{oldIndex:i,newIndex:s}=t;if(void 0===i||void 0===s||i===s)return;const r=this._expandedDevice;if(!r)return;const o=[...r.signals],[a]=o.splice(i,1);o.splice(s,0,a),this._expandedDevice={...r,signals:o},this._signalsSortable?.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null,this._purgeChildren(e,".signal-row"),this._signalsVersion++,this._scheduleSignalsSave(r.id,o.map(e=>e.id))}}))}_purgeChildren(e,t){for(const i of Array.from(e.querySelectorAll(t)))i.remove()}_scheduleRemotesSave(e){null!==this._pendingRemotesSave&&clearTimeout(this._pendingRemotesSave),this._pendingRemotesSave=window.setTimeout(async()=>{this._pendingRemotesSave=null;try{await this.api.reorderUnknownDevices("plucked",e)}catch(e){this._error=`Reorder failed: ${e.message}`,await this._load()}},500)}_scheduleSignalsSave(e,t){null!==this._pendingSignalsSave&&clearTimeout(this._pendingSignalsSave),this._pendingSignalsSave=window.setTimeout(async()=>{this._pendingSignalsSave=null;try{await this.api.reorderUnknownSignals(e,t)}catch(e){this._error=`Reorder failed: ${e.message}`,await this._refreshExpanded()}},500)}async _load(){this._loading=!0;try{const[e,t,i,s]=await Promise.all([this.api.getUnknownDevices({include_dismissed:!1,min_hits:0,source:"plucked"}),this.api.listDevices(),this.api.listTriggers(),this.api.listPluckVendors().catch(()=>({vendors:[]}))]);this._devices=e,this._hairDevices=t,this._triggers=i,this._vendorIntegration=this._mapIntegrations(s.vendors),this._error=null,this.api.listReceivers().then(e=>{this._receivers=e}).catch(()=>{this._receivers=[]})}catch(e){this._error=`Failed to load: ${e.message}`}finally{this._loading=!1}}_mapIntegrations(e){const t={};for(const i of e)for(const e of i.blasters)t[e.entity_id]=i.integration;return t}async _refreshExpanded(){if(this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{this._expandedId=null,this._expandedDevice=null}}openCreateRemote(){this._createRemoteOpen=!0}async _onBlasterCreated(e){this._createRemoteOpen=!1,this.pendingEntity="",await this._load(),this._expandedId=e.detail.id,await this._refreshExpanded()}_openPluckSignal(e,t){t.stopPropagation();const i=e.vendor_entity_id?this._vendorIntegration[e.vendor_entity_id]??"":"";i?this._pluckDialog={device:e,integration:i}:this._error=$e("pluck.vendor_unavailable")}async _onSignalsCreated(){this._pluckDialog=null,await this._refreshExpanded(),await this._load()}_openEditSignal(e,t,i){i.stopPropagation(),this._editSignal={deviceId:e,signal:t}}async _onSignalEdited(){this._editSignal=null,await this._refreshExpanded(),await this._load()}_openDeleteRemote(e){this._deleteRemoteId=e.id,this._deleteRemoteLabel=e.label||"this blaster",this._deleteRemoteCount=e.signals.length}async _confirmDeleteRemote(){const e=this._deleteRemoteId;if(this._deleteRemoteId=null,e)try{await this.api.deletePluckedBlaster(e),this._expandedId===e&&(this._expandedId=null,this._expandedDevice=null),await this._load()}catch(e){this._error=`Delete failed: ${e.message}`}}async _doClearAll(){this._confirmClearAll=!1;try{await this.api.clearUnknowns("plucked"),this._devices=[],this._expandedId=null,this._expandedDevice=null}catch(e){this._error=`Clear failed: ${e.message}`}}_onAliasChanged(e){const{id:t,alias:i}=e.detail;this._expandedDevice&&(this._expandedDevice={...this._expandedDevice,signals:this._expandedDevice.signals.map(e=>e.id===t?{...e,alias:i}:e)})}_startRename(e,t){t.stopPropagation(),this._editingDeviceId=e.id,this._editLabel=e.label??""}async _commitRename(e){const t=this._editLabel.trim();this._editingDeviceId=null;try{const i=await this.api.renameUnknown(e,t),s=this._devices.findIndex(t=>t.id===e);if(s>=0){const e=[...this._devices];e[s]={...e[s],label:i.label},this._devices=e}}catch(e){this._error=`Rename failed: ${e.message}`}}_onRenameKeydown(e,t){"Enter"===t.key?this._commitRename(e):"Escape"===t.key&&(this._editingDeviceId=null)}_openAssign(e,t,i){this._assignSignal={deviceId:e,signal:t,label:i??null}}_onAssignClick(e,t,i,s){if(!t.assigned_to?.length)return void this._openAssign(e,t,i);const r=s?.currentTarget,o=r?.getBoundingClientRect();this._assignedPopover={deviceId:e,signal:t,label:i??null,top:o?o.bottom+4:120,left:o?Math.max(8,o.right-220):120},this._installPopoverDismiss()}_closeAssignedPopover(){this._assignedPopover=null,this._removePopoverDismiss()}_onAssignedPopoverCreateNew(){const e=this._assignedPopover;this._closeAssignedPopover(),e&&this._openAssign(e.deviceId,e.signal,e.label)}_onAssignedPopoverOpen(e){const t=e.detail;this._closeAssignedPopover(),t&&this.dispatchEvent(new CustomEvent("navigate-device",{detail:t.device_id,bubbles:!0,composed:!0}))}async _onSignalAssigned(e){this._assignSignal=null,await this._load(),await this._refreshExpanded()}_matchesHairDevice(e){if(!e)return!1;const t=e.toLowerCase();return this._hairDevices.some(e=>e.name.toLowerCase()===t)}_promoteDevice(e,t){t.stopPropagation(),this._promoteTarget=e}async _onDevicePromoted(){this._promoteTarget=null,await this._load()}_openDelete(e,t){this._deleteSignal={deviceId:e,signal:t}}async _confirmDelete(){if(!this._deleteSignal)return;const{deviceId:e,signal:t}=this._deleteSignal;this._deleteSignal=null;try{await this.api.deleteSignal(e,t.id),await this._load(),await this._refreshExpanded()}catch(e){this._error=`Delete failed: ${e.message}`}}_openTestDialog(e){this._testDialog={signal:e}}async _sendTest(e){if(!this._testDialog)return;const{signal:t}=this._testDialog,i=e.detail.emitters;if(0!==i.length){this._testingSignalId=t.id,this._testResult=null,this._testDialog=null;try{const e=(await Promise.allSettled(i.map(e=>this.api.testSignal(t.id,e)))).filter(e=>"fulfilled"===e.status&&e.value.sent).length,s=i.length;this._testResult=e===s?1===s?$e("mirror.sent"):$e("mirror.sent_all_n",{sent:e,total:s}):0===e?$e("mirror.failed"):`Sent (${e}/${s})`}catch{this._testResult="Error"}setTimeout(()=>{this._testResult=null,this._testingSignalId=null},3e3)}}_hasTrigger(e){return this._triggers.some(t=>_s(t,e))}_triggerCountFor(e){return this._triggers.filter(t=>_s(t,e)).length}_openTriggerDialog(e,t,i){const s=this._triggers.filter(e=>_s(e,t));if(0===s.length)return void(this._triggerDialog={signal:t,deviceId:e});const r=i?.currentTarget,o=r?.getBoundingClientRect();this._triggerPopover={deviceId:e,signal:t,top:o?o.bottom+4:120,left:o?Math.max(8,o.right-220):120},this._installPopoverDismiss()}_closeTriggerPopover(){this._triggerPopover=null,this._removePopoverDismiss()}_onPopoverCreateNew(){const e=this._triggerPopover;this._closeTriggerPopover(),e&&(this._triggerDialog={signal:e.signal,deviceId:e.deviceId})}_onPopoverEditTrigger(e){const t=e.detail;this._closeTriggerPopover(),t&&(this._triggerEditDialog=t)}_installPopoverDismiss(){setTimeout(()=>{document.addEventListener("click",this._onDocClickForPopover,!0),window.addEventListener("scroll",this._onScrollForPopover,!0)},0)}_removePopoverDismiss(){document.removeEventListener("click",this._onDocClickForPopover,!0),window.removeEventListener("scroll",this._onScrollForPopover,!0)}async _subscribeUpdated(){try{this._unsubUpdated=await this.api.subscribeSignalUpdated(()=>{this._refreshAfterSignalUpdate()})}catch{}}async _unsubscribeUpdated(){this._unsubUpdated&&(await this._unsubUpdated(),this._unsubUpdated=null)}async _refreshAfterSignalUpdate(){try{this._triggers=await this.api.listTriggers()}catch{}if(this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{}}_closeTriggerDialog(){this._triggerDialog=null,this._triggerEditDialog=null}_requestDeleteTrigger(e){this._confirmDeleteTriggerId=e}async _doDeleteTrigger(){if(!this._confirmDeleteTriggerId)return;const e=this._confirmDeleteTriggerId;this._confirmDeleteTriggerId=null,this._triggerEditDialog=null;try{await this.api.deleteTrigger(e),this._triggers=await this.api.listTriggers()}catch{}}async _onTriggerSaved(){this._triggerDialog=null,this._triggerEditDialog=null;try{this._triggers=await this.api.listTriggers()}catch{}}async _toggleExpand(e){if(this._expandedId===e)return this._expandedId=null,void(this._expandedDevice=null);this._expandedId=e,await this._refreshExpanded()}render(){const e=this._devices.length;return F`
            <div class="toolbar">
                <span class="title">
                    <ha-svg-icon .path=${Ts}></ha-svg-icon>
                    ${$e("pluck.title")}
                    ${this._loading?"":F`<span class="count"
                              >(${e} ${1===e?"blaster":"blasters"})</span
                          >`}
                </span>
                <div class="toolbar-actions">
                    <button
                        class="action-btn create-btn"
                        @click=${()=>this._createRemoteOpen=!0}
                    >
                        ${$e("pluck.add_blaster")}
                    </button>
                </div>
            </div>

            ${this._error?F`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

            ${this._loading?F`<div class="loading">${$e("common.loading_plain")}</div>`:0===e?F`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${Ts}></ha-svg-icon>
                            <h3>${$e("pluck.empty_title")}</h3>
                            <p>${$e("pluck.empty_body")}</p>
                            <p class="hint">${$e("pluck.empty_hint")}</p>
                        </ha-card>
                    `:F`
                        <div class="device-list">
                            ${He(this._remotesVersion,Ne(this._devices,e=>e.id,e=>this._renderDevice(e)))}
                        </div>
                    `}

            ${e>0?F`
                      <div class="clear-all-row">
                          <button
                              class="action-btn delete-btn"
                              title=${$e("pluck.clear_all_title")}
                              @click=${()=>this._confirmClearAll=!0}
                          >
                              Clear All
                          </button>
                      </div>
                  `:""}

            ${this._renderDialogs()}
        `}_renderDevice(e){const t=this._expandedId===e.id;return F`
            <ha-card class="device pluck-device">
                <div class="device-row" @click=${()=>this._toggleExpand(e.id)}>
                    <div class="device-info">
                        <div class="device-header">
                            ${this._editingDeviceId===e.id?F`<input
                                      class="rename-input"
                                      type="text"
                                      .value=${this._editLabel}
                                      @input=${e=>{this._editLabel=e.target.value}}
                                      @keydown=${t=>this._onRenameKeydown(e.id,t)}
                                      @blur=${()=>{this._commitRename(e.id)}}
                                      @click=${e=>e.stopPropagation()}
                                  />`:F`<ha-svg-icon
                                          class="remote-grip"
                                          .path=${Es}
                                          title=${$e("devdetail.drag")}
                                          @click=${e=>e.stopPropagation()}
                                      ></ha-svg-icon>
                                      <span
                                          class="protocol"
                                          title=${$e("cmdrow.rename")}
                                          @click=${t=>this._startRename(e,t)}
                                          >${e.label??$e("pluck.blaster_fallback")}</span
                                      >`}
                            ${e.appliance?F`<span
                                      class="appliance-badge"
                                      @click=${e=>e.stopPropagation()}
                                      >${e.appliance}</span
                                  >`:""}
                            <span class="stat"
                                ><strong>${e.signal_count}</strong>
                                ${1===e.signal_count?"signal":"signals"}</span
                            >
                            ${e.label&&this._matchesHairDevice(e.label)?F`<span
                                      class="status-badge hair-device"
                                      @click=${e=>e.stopPropagation()}
                                      >${$e("sniffer.hair_device")}</span
                                  >`:e.label?F`<span
                                        class="status-badge promote-badge"
                                        title=${$e("pluck.promote_title")}
                                        @click=${t=>this._promoteDevice(e,t)}
                                        >${$e("sniffer.promote")}</span
                                    >`:""}
                        </div>
                    </div>
                    <ha-svg-icon
                        class="expand-icon"
                        .path=${t?"M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z":"M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z"}
                    ></ha-svg-icon>
                </div>

                ${t&&this._expandedDevice?this._renderExpanded(this._expandedDevice):""}
            </ha-card>
        `}_renderExpanded(e){return F`
            <div class="expanded">
                <div class="signal-header">
                    <span>${$e("sniffer.signals_head",{count:e.signals.length})}</span>
                    <button
                        class="create-signal-btn"
                        title=${$e("pluck.pluck_signal_title")}
                        @click=${t=>this._openPluckSignal(e,t)}
                    >
                        ${$e("pluck.pluck_signal")}
                    </button>
                </div>
                ${0===e.signals.length?F`<div class="no-signals-row">
                          <span class="no-signals"
                              >${$e("pluck.no_signals")}</span
                          >
                      </div>`:F`
                          <div class="signal-list">
                              ${He(this._signalsVersion,Ne(e.signals,e=>e.id,t=>this._renderSignal(e.id,t,e.label)))}
                          </div>
                      `}
                <div class="remote-footer">
                    <button
                        class="action-btn delete-btn"
                        title=${$e("pluck.delete_blaster_title")}
                        @click=${t=>{t.stopPropagation(),this._openDeleteRemote(e)}}
                    >
                        ${$e("pluck.delete_blaster")}
                    </button>
                </div>
            </div>
        `}_renderSignal(e,t,i){const s=this._testingSignalId===t.id;return F`
            <div class="signal-row">
                <ha-svg-icon
                    class="signal-grip"
                    .path=${Es}
                    title=${$e("devdetail.drag")}
                ></ha-svg-icon>
                <div class="signal-info">
                    <ir-signal-alias
                        .api=${this.api}
                        .deviceId=${e}
                        .signal=${t}
                        @alias-changed=${this._onAliasChanged}
                        @alias-error=${e=>this._error=e.detail}
                    ></ir-signal-alias>
                </div>
                <div class="signal-meta">
                    ${s&&this._testResult?F`<span class="test-result">${this._testResult}</span>`:F`<span>${Math.round(t.frequency/1e3)} kHz</span>`}
                </div>
                ${t.code?F`<button
                          title=${$e("cmdrow.edit_code")}
                          @click=${i=>this._openEditSignal(e,t,i)}
                          style="background:none;border:none;cursor:pointer;color:var(--secondary-text-color);padding:2px;display:inline-flex;align-items:center"
                      >
                          <ha-svg-icon
                              .path=${"M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"}
                              style="--mdc-icon-size:10px"
                          ></ha-svg-icon>
                      </button>`:""}
                <div class="signal-actions">
                    <button
                        class="action-btn assign-btn"
                        title=${t.assignment_count&&t.assigned_to?.length?1===t.assignment_count?`Assigned to ${t.assigned_to[0].device_name} / ${t.assigned_to[0].command_name}`:`Assigned to ${t.assignment_count} commands:\n- ${t.assigned_to.map(e=>`${e.device_name} / ${e.command_name}`).join("\n- ")}`:$e("mirror.assign_title")}
                        @click=${s=>{s.stopPropagation(),this._onAssignClick(e,t,i,s)}}
                    >
                        ${$e("assign.assign")}<ir-count-dot
                            color="green"
                            .count=${t.assignment_count??0}
                        ></ir-count-dot>
                    </button>
                    <button
                        class="action-btn test-btn"
                        ?disabled=${s}
                        title=${$e("clips.test_title")}
                        @click=${e=>{e.stopPropagation(),this._openTestDialog(t)}}
                    >
                        ${s?this._testResult??$e("mirror.sending"):$e("mirror.test")}
                    </button>
                    <button
                        class="action-btn trigger-btn"
                        title=${this._hasTrigger(t)?$e("mirror.trigger_edit"):$e("sniffer.trigger_create")}
                        @click=${i=>{i.stopPropagation(),this._openTriggerDialog(e,t,i)}}
                    >
                        ${$e("cmdrow.trigger")}<ir-count-dot
                            color="yellow"
                            .count=${this._triggerCountFor(t)}
                        ></ir-count-dot>
                    </button>
                    <button
                        class="action-btn delete-btn"
                        @click=${i=>{i.stopPropagation(),this._openDelete(e,t)}}
                    >
                        ${$e("common.delete")}
                    </button>
                </div>
            </div>
        `}_renderDialogs(){return F`
            ${this._createRemoteOpen?F`<ir-pluck-add-remote-dialog
                      .api=${this.api}
                      .pendingEntity=${this.pendingEntity}
                      @blaster-created=${this._onBlasterCreated}
                      @closed=${()=>{this._createRemoteOpen=!1,this.pendingEntity=""}}
                  ></ir-pluck-add-remote-dialog>`:""}

            ${this._promoteTarget?F`<ir-promote-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .suggestedName=${this._promoteTarget.label??""}
                      @device-created=${this._onDevicePromoted}
                      @closed=${()=>this._promoteTarget=null}
                  ></ir-promote-dialog>`:""}

            ${this._pluckDialog?F`<ir-pluck-signal-dialog
                      .api=${this.api}
                      .blaster=${this._pluckDialog.device}
                      .integration=${this._pluckDialog.integration}
                      @signals-created=${this._onSignalsCreated}
                      @closed=${()=>this._pluckDialog=null}
                  ></ir-pluck-signal-dialog>`:""}

            ${this._editSignal?F`<ir-signal-editor
                      .api=${this.api}
                      .deviceId=${this._editSignal.deviceId}
                      .signalId=${this._editSignal.signal.id}
                      .initialPronto=${this._editSignal.signal.code??""}
                      .initialAlias=${this._editSignal.signal.alias??""}
                      .initialSendCount=${this._editSignal.signal.send_count??1}
                      .initialDitto=${this._editSignal.signal.repeat_count??1}
                      .initialObservedRepeatCount=${this._editSignal.signal.observed_repeat_count??0}
                      .hasTrigger=${this._hasTrigger(this._editSignal.signal)}
                      @signal-edited=${this._onSignalEdited}
                      @closed=${()=>this._editSignal=null}
                  ></ir-signal-editor>`:""}

            ${this._assignSignal?F`<ir-assign-signal-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .unknownDeviceId=${this._assignSignal.deviceId}
                      .signal=${this._assignSignal.signal}
                      .suggestedDeviceName=${this._assignSignal.label??""}
                      .initialMode=${"existing"}
                      @signal-assigned=${this._onSignalAssigned}
                      @closed=${()=>this._assignSignal=null}
                  ></ir-assign-signal-dialog>`:""}

            ${this._deleteSignal?F`<ir-confirm-dialog
                      title=${$e("sniffer.del_signal_title")}
                      message=${$e("sniffer.del_signal_msg")}
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._confirmDelete}
                      @closed=${()=>this._deleteSignal=null}
                  ></ir-confirm-dialog>`:""}

            ${this._confirmClearAll?F`<ir-confirm-dialog
                      title=${$e("pluck.clear_all_confirm_title")}
                      message=${$e("pluck.clear_all_confirm_msg")}
                      confirmLabel="Clear All"
                      .destructive=${!0}
                      @confirmed=${this._doClearAll}
                      @closed=${()=>this._confirmClearAll=!1}
                  ></ir-confirm-dialog>`:""}

            ${this._deleteRemoteId?F`<ir-confirm-dialog
                      title=${$e("pluck.del_blaster_confirm_title")}
                      message=${this._deleteRemoteCount>0?ke("clips.del_remote_msg_n",this._deleteRemoteCount,{name:this._deleteRemoteLabel??""}):$e("clips.del_remote_msg",{name:this._deleteRemoteLabel??""})}
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._confirmDeleteRemote}
                      @closed=${()=>this._deleteRemoteId=null}
                  ></ir-confirm-dialog>`:""}

            ${this._triggerPopover?F`<ir-trigger-popover
                      .triggers=${this._triggers.filter(e=>_s(e,this._triggerPopover.signal))}
                      .receivers=${this._receivers}
                      .top=${this._triggerPopover.top}
                      .left=${this._triggerPopover.left}
                      @create-new=${this._onPopoverCreateNew}
                      @edit-trigger=${this._onPopoverEditTrigger}
                  ></ir-trigger-popover>`:""}

            ${this._assignedPopover?F`<ir-assigned-popover
                      .assignments=${this._assignedPopover.signal.assigned_to??[]}
                      .top=${this._assignedPopover.top}
                      .left=${this._assignedPopover.left}
                      @create-new=${this._onAssignedPopoverCreateNew}
                      @open-assignment=${this._onAssignedPopoverOpen}
                  ></ir-assigned-popover>`:""}

            ${this._triggerDialog?F`<ir-trigger-dialog
                      .api=${this.api}
                      .signalFingerprint=${this._triggerDialog.signal.fingerprint}
                      .byteHash=${this._triggerDialog.signal.byte_hash??null}
                      .decodedFingerprint=${this._triggerDialog.signal.decoded_fingerprint??null}
                      .protocol=${this._triggerDialog.signal.protocol}
                      .code=${this._triggerDialog.signal.code}
                      .slPattern=${this._triggerDialog.signal.sl_pattern??null}
                      .alias=${this._triggerDialog.signal.alias||null}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                  ></ir-trigger-dialog>`:""}

            ${this._triggerEditDialog?F`<ir-trigger-dialog
                      .api=${this.api}
                      .trigger=${this._triggerEditDialog}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                      @trigger-delete=${e=>this._requestDeleteTrigger(e.detail.triggerId)}
                  ></ir-trigger-dialog>`:""}

            ${this._confirmDeleteTriggerId?F`<ir-confirm-dialog
                      title=${$e("mirror.del_trigger_title")}
                      message=${$e("devdetail.del_trigger_msg")}
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._doDeleteTrigger}
                      @closed=${()=>this._confirmDeleteTriggerId=null}
                  ></ir-confirm-dialog>`:""}

            ${this._testDialog?F`<ir-test-emitter-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .value=${this._testEmitters}
                      @emitters-changed=${e=>this._testEmitters=e.detail.value}
                      @send=${this._sendTest}
                      @closed=${()=>this._testDialog=null}
                  ></ir-test-emitter-dialog>`:""}
        `}};function Ps(e){if(!e)return"";try{const t=Date.now()-new Date(e).getTime();return t<6e4?$e("rel.just_now"):t<36e5?`${Math.floor(t/6e4)}m`:t<864e5?`${Math.floor(t/36e5)}h`:`${Math.floor(t/864e5)}d`}catch{return""}}Is.styles=[Vi,a`
        :host {
            display: block;
        }
        .toolbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            flex-wrap: wrap;
            gap: 8px;
        }
        .toolbar-actions {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .title {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--primary-text-color);
        }
        .title ha-svg-icon {
            --mdc-icon-size: 24px;
            color: #455a64;
        }
        .count {
            font-weight: 400;
            color: var(--secondary-text-color);
            font-size: 0.9rem;
        }
        /* Toolbar "+ Add Blaster": shared chip anatomy, slate accent. */
        .action-btn.create-btn {
            color: #78909c;
            border-color: #78909c;
        }
        .action-btn.create-btn:hover:not(:disabled) {
            background: rgba(120, 144, 156, 0.12);
        }
        /* Card-internal "+ Pluck Signal": borderless slate text action
           (no chip, no stroke -- owner ruling), one pixel up from its
           old size, font color matching the Add Blaster accent. */
        .create-signal-btn {
            border: none;
            background: none;
            padding: 0;
            font-size: 10px;
            font-weight: 500;
            font-family: inherit;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            color: #78909c;
            cursor: pointer;
        }
        .create-signal-btn:hover:not(:disabled) {
            background: none;
            text-decoration: underline;
        }
        .clear-all-row {
            display: flex;
            justify-content: flex-end;
            margin-top: 16px;
        }
        .loading,
        .empty {
            padding: 48px 24px;
            text-align: center;
            color: var(--secondary-text-color);
        }
        .empty-icon {
            --mdc-icon-size: 48px;
            color: #455a64;
            opacity: 0.5;
            margin-bottom: 16px;
        }
        .empty h3 {
            color: var(--primary-text-color);
            margin: 8px 0;
        }
        .hint {
            font-size: 0.85rem;
            font-style: italic;
        }
        .device-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }
        .device.pluck-device {
            border: 1px solid rgba(69, 90, 100, 0.3);
            overflow: hidden;
        }
        .device-row {
            display: flex;
            align-items: center;
            padding: 12px 16px;
            cursor: pointer;
            gap: 12px;
        }
        .device-row:hover {
            background: var(--secondary-background-color);
        }
        .device-info {
            flex: 1;
            min-width: 0;
        }
        .device-header {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .remote-grip {
            --mdc-icon-size: 18px;
            color: #455a64;
            cursor: grab;
            flex-shrink: 0;
            opacity: 0.85;
            transition: opacity 120ms ease;
        }
        .remote-grip:hover {
            opacity: 1;
        }
        .remote-grip:active {
            cursor: grabbing;
        }
        .signal-grip {
            --mdc-icon-size: 16px;
            color: var(--secondary-text-color);
            cursor: grab;
            flex-shrink: 0;
            opacity: 0.6;
            transition: opacity 120ms ease;
        }
        .signal-grip:hover {
            opacity: 1;
        }
        .signal-grip:active {
            cursor: grabbing;
        }
        ha-card.sortable-ghost,
        .signal-row.sortable-ghost {
            opacity: 0.4;
        }
        .protocol {
            font-weight: 600;
            font-size: 0.95rem;
            cursor: text;
            border-bottom: 1px dashed transparent;
            transition: border-color 150ms ease;
        }
        .protocol:hover {
            border-bottom-color: #455a64;
        }
        .rename-input {
            font-weight: 600;
            font-size: 0.95rem;
            font-family: inherit;
            border: 1px solid #455a64;
            border-radius: 4px;
            padding: 2px 6px;
            background: var(--card-background-color, #fff);
            color: var(--primary-text-color);
            outline: none;
            width: 160px;
        }
        .appliance-badge {
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
            letter-spacing: 0.02em;
            white-space: nowrap;
            flex-shrink: 0;
            background: rgba(69, 90, 100, 0.15);
            color: #455a64;
            border: 1px solid rgba(69, 90, 100, 0.35);
        }
        .status-badge.hair-device {
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            white-space: nowrap;
            flex-shrink: 0;
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
            border: 1px solid rgba(46, 125, 50, 0.3);
        }
        .status-badge.promote-badge {
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            background: rgba(0, 151, 167, 0.15);
            color: #0097a7;
            border: 1px solid rgba(0, 151, 167, 0.35);
            cursor: pointer;
            transition: background 150ms ease;
        }
        .status-badge.promote-badge:hover {
            background: rgba(0, 151, 167, 0.25);
        }
        .stat {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
        }
        .stat strong {
            color: var(--primary-text-color);
        }
        .expand-icon {
            --mdc-icon-size: 24px;
            color: var(--secondary-text-color);
            flex-shrink: 0;
        }
        .expanded {
            border-top: 1px solid var(--divider-color);
            padding: 12px 16px 16px;
        }
        .signal-header {
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.85rem;
            font-weight: 500;
            margin-bottom: 8px;
        }
        .no-signals-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
            padding: 6px 8px;
        }
        .no-signals {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            font-style: italic;
        }
        .remote-footer {
            display: flex;
            justify-content: flex-end;
            margin-top: 10px;
            padding-right: 8px;
        }
        .signal-list {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .signal-row {
            display: flex;
            align-items: center;
            padding: 6px 8px;
            background: var(--primary-background-color);
            border-radius: 4px;
            gap: 8px;
            flex-wrap: wrap;
        }
        @media (max-width: 768px) {
            .signal-row {
                display: grid;
                grid-template-columns: 1fr auto;
                align-items: start;
                gap: 6px 8px;
            }
            .signal-actions {
                grid-column: 1 / -1;
                justify-content: flex-start;
                flex-wrap: wrap;
            }
        }
        .signal-info {
            flex: 1;
            min-width: 0;
        }
        .signal-meta {
            display: flex;
            gap: 12px;
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            white-space: nowrap;
        }
        .test-result {
            color: #2e7d32;
            font-weight: 500;
        }
        .signal-actions {
            display: flex;
            gap: 4px;
            flex-shrink: 0;
        }
    `],e([pe({attribute:!1})],Is.prototype,"api",void 0),e([pe({attribute:!1})],Is.prototype,"hass",void 0),e([pe()],Is.prototype,"pendingEntity",void 0),e([he()],Is.prototype,"_devices",void 0),e([he()],Is.prototype,"_hairDevices",void 0),e([he()],Is.prototype,"_triggers",void 0),e([he()],Is.prototype,"_loading",void 0),e([he()],Is.prototype,"_error",void 0),e([he()],Is.prototype,"_expandedId",void 0),e([he()],Is.prototype,"_expandedDevice",void 0),e([he()],Is.prototype,"_confirmClearAll",void 0),e([he()],Is.prototype,"_deleteRemoteId",void 0),e([he()],Is.prototype,"_deleteRemoteLabel",void 0),e([he()],Is.prototype,"_deleteRemoteCount",void 0),e([he()],Is.prototype,"_editingDeviceId",void 0),e([he()],Is.prototype,"_editLabel",void 0),e([he()],Is.prototype,"_createRemoteOpen",void 0),e([he()],Is.prototype,"_promoteTarget",void 0),e([he()],Is.prototype,"_pluckDialog",void 0),e([he()],Is.prototype,"_editSignal",void 0),e([he()],Is.prototype,"_assignSignal",void 0),e([he()],Is.prototype,"_deleteSignal",void 0),e([he()],Is.prototype,"_triggerDialog",void 0),e([he()],Is.prototype,"_triggerEditDialog",void 0),e([he()],Is.prototype,"_triggerPopover",void 0),e([he()],Is.prototype,"_assignedPopover",void 0),e([he()],Is.prototype,"_receivers",void 0),e([he()],Is.prototype,"_confirmDeleteTriggerId",void 0),e([he()],Is.prototype,"_testDialog",void 0),e([he()],Is.prototype,"_testEmitters",void 0),e([he()],Is.prototype,"_testingSignalId",void 0),e([he()],Is.prototype,"_testResult",void 0),e([he()],Is.prototype,"_remotesVersion",void 0),e([he()],Is.prototype,"_signalsVersion",void 0),Is=e([me("ir-pluck")],Is);const Rs="M 19.39,4.60 C 16.51,1.71 11.78,1.71 8.89,4.60 C 6.00,7.49 6.00,12.21 8.89,15.10 C 11.78,17.99 16.51,17.99 19.39,15.10 C 22.28,12.21 22.28,7.49 19.39,4.60 M 9.29,14.70 C 6.63,12.03 6.63,7.67 9.29,5.00 C 11.96,2.34 16.32,2.34 18.99,5.00 C 21.66,7.67 21.66,12.03 18.99,14.70 C 16.32,17.36 11.96,17.36 9.29,14.70 M 4.85,19.14 C 4.29,18.58 3.40,18.58 2.83,19.14 C 2.27,19.71 2.27,20.60 2.83,21.16 C 3.40,21.73 4.29,21.73 4.85,21.16 C 5.42,20.60 5.42,19.71 4.85,19.14 M 3.24,20.76 C 2.89,20.41 2.89,19.89 3.24,19.55 C 3.58,19.20 4.10,19.20 4.45,19.55 C 4.79,19.89 4.79,20.41 4.45,20.76 C 4.10,21.10 3.58,21.10 3.24,20.76 M 22.99,9.57 C 22.91,7.10 21.84,4.82 19.98,3.20 C 16.65,0.28 11.62,0.26 8.31,3.20 C 5.52,5.67 4.57,9.49 5.86,12.96 C 6.33,14.19 6.02,15.55 5.13,16.43 C 4.65,16.92 4.04,17.24 3.40,17.32 C 2.79,17.40 2.25,17.71 1.82,18.13 C 0.75,19.20 0.73,21.00 1.78,22.09 C 1.80,22.11 1.82,22.13 1.84,22.15 C 2.37,22.68 3.07,22.98 3.82,23.00 C 4.61,23.02 5.32,22.72 5.88,22.15 C 6.31,21.73 6.57,21.18 6.67,20.60 C 6.77,19.93 7.07,19.34 7.56,18.86 C 8.45,17.97 9.82,17.69 11.03,18.13 C 14.28,19.36 17.96,18.56 20.40,16.11 C 22.12,14.39 23.07,11.99 22.99,9.57 M 11.23,17.61 C 9.82,17.08 8.20,17.40 7.15,18.45 C 6.59,19.02 6.22,19.75 6.10,20.51 C 6.02,21.00 5.80,21.42 5.46,21.77 C 5.01,22.21 4.43,22.43 3.82,22.43 C 3.17,22.43 2.61,22.19 2.18,21.73 C 1.34,20.84 1.38,19.42 2.21,18.56 C 2.55,18.21 2.99,17.97 3.48,17.89 C 4.25,17.77 4.97,17.40 5.54,16.84 C 6.59,15.79 6.93,14.19 6.39,12.76 C 5.17,9.53 6.06,5.93 8.69,3.63 C 11.80,0.88 16.49,0.88 19.60,3.63 C 19.74,3.73 19.88,3.87 20.00,3.99 C 21.49,5.49 22.36,7.45 22.42,9.57 C 22.48,11.89 21.64,14.07 20.00,15.71 C 17.70,18.01 14.26,18.74 11.23,17.61 M 17.58,10.86 L 10.71,10.86 C 10.55,10.86 10.43,10.98 10.43,11.14 C 10.43,11.22 10.47,11.30 10.51,11.34 C 10.55,11.38 10.63,11.43 10.71,11.43 L 17.58,11.43 C 17.74,11.43 17.86,11.30 17.86,11.14 C 17.86,10.98 17.72,10.88 17.58,10.86 M 17.88,8.54 C 17.88,8.38 17.76,8.25 17.60,8.25 L 10.73,8.25 C 10.57,8.25 10.45,8.38 10.45,8.54 C 10.45,8.62 10.49,8.70 10.53,8.74 C 10.57,8.78 10.65,8.82 10.73,8.82 L 17.60,8.82 C 17.72,8.82 17.86,8.68 17.88,8.54";let Ms=class extends ne{constructor(){super(...arguments),this._device=null,this._loading=!0,this._error=null,this._triggers=[],this._receivers=[],this._hasReceivers=!0,this._filter="all",this._search="",this._bloomIds=new Set,this._assignSignal=null,this._assignedPopover=null,this._triggerDialog=null,this._triggerEditDialog=null,this._triggerPopover=null,this._confirmDeleteTriggerId=null,this._deleteSignal=null,this._editSignal=null,this._testDialog=null,this._testEmitters=[],this._testingSignalId=null,this._testResult=null,this._unsubSignals=null,this._unsubUpdated=null,this._refreshTimer=null,this._onDocClickForPopover=e=>{const t=e.composedPath(),i=this.shadowRoot?.querySelector("ir-trigger-popover"),s=this.shadowRoot?.querySelector("ir-assigned-popover");i&&t.includes(i)||s&&t.includes(s)||(this._closeTriggerPopover(),this._closeAssignedPopover())},this._onScrollForPopover=()=>{this._closeTriggerPopover(),this._closeAssignedPopover()}}connectedCallback(){super.connectedCallback(),this._load(),this._subscribe()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribe(),this._removePopoverDismiss(),null!==this._refreshTimer&&(clearTimeout(this._refreshTimer),this._refreshTimer=null)}async _load(){this._loading=!0;try{const[e,t,i]=await Promise.all([this.api.getUnknownDevices({source:"echo",min_hits:0}),this.api.listTriggers(),this.api.getSnifferStatus()]);this._triggers=t,this._hasReceivers=i.has_receivers;const s=e.find(e=>e.fingerprint===us);this._device=s?await this.api.getUnknownDevice(s.id):null,this._error=null,this.api.listReceivers().then(e=>{this._receivers=e}).catch(()=>{this._receivers=[]})}catch(e){this._error=`Failed to load: ${e.message}`}finally{this._loading=!1}}async _refreshDevice(){if(this._device)try{this._device=await this.api.getUnknownDevice(this._device.id)}catch{await this._load()}else await this._load()}async _subscribe(){try{this._unsubSignals=await this.api.subscribeUnknownSignals(e=>this._onLiveSignal(e))}catch{}try{this._unsubUpdated=await this.api.subscribeSignalUpdated(()=>{this._refreshDots()})}catch{}}async _unsubscribe(){this._unsubSignals&&(await this._unsubSignals(),this._unsubSignals=null),this._unsubUpdated&&(await this._unsubUpdated(),this._unsubUpdated=null)}async _refreshDots(){try{this._triggers=await this.api.listTriggers()}catch{}await this._refreshDevice()}_onLiveSignal(e){e.device_fingerprint===us&&(this._bloomIds=new Set([...this._bloomIds,e.signal_id]),setTimeout(()=>{const t=new Set(this._bloomIds);t.delete(e.signal_id),this._bloomIds=t},2500),null!==this._refreshTimer&&clearTimeout(this._refreshTimer),this._refreshTimer=window.setTimeout(()=>{this._refreshTimer=null,this._refreshDevice()},300))}_friendlyReceiver(e){const t=this._receivers.find(t=>t.entity_id===e);if(t?.name)return t.name;const i=this.hass?.states?.[e];return i?.attributes?.friendly_name??e}_receiverArea(e){const t=this.hass?.entities?.[e],i=t?.area_id??(t?.device_id?this.hass?.devices?.[t.device_id]?.area_id:null);return i?this.hass?.areas?.[i]?.name??null:null}_decodedDisplay(e){const t=e.decoded_fingerprint;if(!t)return null;const i=t.split(":");return i.length>=3?`${i[0]} ${i[1]} : ${i.slice(2).join(":")}`:t}_rowView(e){const t=e.echo_source??"",i=t.indexOf(" -- via "),s=i>=0?t.slice(0,i):t,r=i>=0?t.slice(i+8):"",o=r?r.split(", "):[];let a,n=null;const l=["Manual test send","Catalog test"].find(e=>s.startsWith(e));"automation send"===s?a=$e("mirror.chip_automation"):"integration send"===s?a=$e("mirror.chip_integration"):l?(a=$e("mirror.chip_test"),n=s.slice(l.length).replace(/^:\s*/,"").trim()||null):s?(a=$e("mirror.chip_device"),n=s):a=$e("mirror.chip_send");const d=(e.fingerprint??"").startsWith("mirror-unknown::"),c=(d&&"Unknown send"===e.alias?"":e.alias)||n||this._decodedDisplay(e)||(e.sl_pattern?[...e.sl_pattern].map(e=>"L"===e?"◆":"◇").join(""):null)||$e("mirror.unknown_title"),p=e.decoded_protocol??e.protocol,h=!e.decoded_protocol,g=o.length>2?$e("mirror.via_n",{count:o.length}):r?$e("mirror.via",{name:r}):"";let m=null,u=!1;if(this._hasReceivers){const t=e.heard_by??[];if(0===t.length)m=$e("mirror.not_heard");else{u=!0;const e=t.map(e=>this._receiverArea(e));if(e.every(e=>null!==e))m=$e("mirror.heard_in",{areas:[...new Set(e)].join(", ")});else{const e=t.map(e=>this._friendlyReceiver(e));m=$e("mirror.heard_by",{names:e.join(", ")})}}}return{sig:e,title:c,pill:p??null,pillRaw:h,via:g,viaFull:r,emitters:o,chip:a,heard:m,heardOk:u,unknownSend:d}}_rows(){const e=[...this._device?.signals??[]].sort((e,t)=>(t.last_seen??"").localeCompare(e.last_seen??""));return e.map(e=>this._rowView(e))}_filteredRows(e){let t=e;"notheard"===this._filter?t=t.filter(e=>0===(e.sig.heard_by??[]).length):"all"!==this._filter&&(t=t.filter(e=>e.emitters.includes(this._filter)));const i=this._search.trim().toLowerCase();return i&&(t=t.filter(e=>[e.title,e.pill??"",e.viaFull,e.chip,e.sig.decoded_fingerprint??"",e.sig.alias??""].join(" ").toLowerCase().includes(i))),t}_triggerCountFor(e){return this._triggers.filter(t=>_s(t,e)).length}_onAssignClick(e,t){if(!this._device)return;if(!e.assigned_to?.length)return void(this._assignSignal={signal:e,initialMode:"existing"});const i=t?.currentTarget,s=i?.getBoundingClientRect();this._assignedPopover={signal:e,top:s?s.bottom+4:120,left:s?Math.max(8,s.right-220):120},this._installPopoverDismiss()}_closeAssignedPopover(){this._assignedPopover=null,this._removePopoverDismiss()}_onAssignedPopoverCreateNew(){const e=this._assignedPopover;this._closeAssignedPopover(),e&&(this._assignSignal={signal:e.signal,initialMode:"existing"})}_onAssignedPopoverOpen(e){const t=e.detail;this._closeAssignedPopover(),t&&this.dispatchEvent(new CustomEvent("navigate-device",{detail:t.device_id,bubbles:!0,composed:!0}))}async _onSignalAssigned(e){this._assignSignal=null,await this._refreshDots()}_openTriggerDialog(e,t){const i=this._triggers.filter(t=>_s(t,e));if(0===i.length)return void(this._triggerDialog=e);const s=t?.currentTarget,r=s?.getBoundingClientRect();this._triggerPopover={signal:e,top:r?r.bottom+4:120,left:r?Math.max(8,r.right-220):120},this._installPopoverDismiss()}_closeTriggerPopover(){this._triggerPopover=null,this._removePopoverDismiss()}_onPopoverCreateNew(){const e=this._triggerPopover;this._closeTriggerPopover(),e&&(this._triggerDialog=e.signal)}_onPopoverEditTrigger(e){const t=e.detail;this._closeTriggerPopover(),t&&(this._triggerEditDialog=t)}async _onTriggerSaved(){this._triggerDialog=null,this._triggerEditDialog=null;try{this._triggers=await this.api.listTriggers()}catch{}}_closeTriggerDialog(){this._triggerDialog=null,this._triggerEditDialog=null}_requestDeleteTrigger(e){this._closeTriggerDialog(),this._confirmDeleteTriggerId=e}async _confirmDeleteTrigger(){const e=this._confirmDeleteTriggerId;if(this._confirmDeleteTriggerId=null,e)try{await this.api.deleteTrigger(e),this._triggers=await this.api.listTriggers()}catch(e){this._error=$e("common.delete_failed",{message:e.message})}}_installPopoverDismiss(){setTimeout(()=>{document.addEventListener("click",this._onDocClickForPopover,!0),window.addEventListener("scroll",this._onScrollForPopover,!0)},0)}_removePopoverDismiss(){document.removeEventListener("click",this._onDocClickForPopover,!0),window.removeEventListener("scroll",this._onScrollForPopover,!0)}async _sendTest(e){if(!this._testDialog)return;const t=this._testDialog,i=e.detail.emitters;if(0!==i.length){this._testingSignalId=t.id,this._testResult=null,this._testDialog=null;try{const e=(await Promise.allSettled(i.map(e=>this.api.testSignal(t.id,e)))).filter(e=>"fulfilled"===e.status&&e.value.sent).length,s=i.length;this._testResult=e===s?1===s?$e("mirror.sent"):$e("mirror.sent_all_n",{sent:e,total:s}):0===e?$e("mirror.failed"):$e("mirror.sent_partial",{sent:e,total:s})}catch{this._testResult=$e("mirror.error")}setTimeout(()=>{this._testResult=null,this._testingSignalId=null},3e3)}}async _onSignalEdited(){this._editSignal=null,await this._refreshDevice()}async _confirmDeleteSignal(){const e=this._deleteSignal;if(this._deleteSignal=null,e&&this._device)try{await this.api.deleteSignal(this._device.id,e.id),await this._refreshDevice()}catch(e){this._error=$e("common.delete_failed",{message:e.message})}}render(){const e=this._rows(),t=this._filteredRows(e);return F`
            <div class="tab-head">
                <span class="title">
                    <ha-svg-icon .path=${Rs}></ha-svg-icon>
                    HAIR Mirror
                    ${this._loading?"":F`<span class="count"
                              >(${ke("mirror.signals",e.length)})</span
                          >`}
                </span>
            </div>
            ${this._error?F`<div class="error">${this._error}</div>`:""}
            ${this._loading&&!this._device?F`<div class="loading">${$e("panel.loading")}</div>`:0===e.length?this._renderEmpty():F`
                        ${this._renderStats(e)}
                        ${this._renderToolbar(e)}
                        <div class="rows">
                            ${0===t.length?F`<div class="no-match">
                                      ${$e("mirror.no_match")}
                                  </div>`:t.map(e=>this._renderRow(e))}
                        </div>
                    `}
            ${this._renderDialogs()}
        `}_renderStats(e){const t=e.filter(e=>0===(e.sig.heard_by??[]).length).length,i=new Set;for(const t of e)t.emitters.forEach(e=>i.add(e));const s=this._device?.last_seen;return F`
            <div class="stats">
                <div class="stat">
                    <div class="v">${this._device?.hit_count??0}</div>
                    <div class="l">${$e("mirror.stat_sends")}</div>
                </div>
                ${this._hasReceivers?F`
                          <div class="stat">
                              <div class="v ${t?"warn":""}">
                                  ${t}
                              </div>
                              <div class="l">${$e("mirror.stat_not_heard")}</div>
                          </div>
                      `:""}
                <div class="stat">
                    <div class="v">${i.size}</div>
                    <div class="l">${$e("mirror.stat_emitters")}</div>
                </div>
                <div class="stat">
                    <div class="v">${e.length}</div>
                    <div class="l">${$e("mirror.stat_signals")}</div>
                </div>
                <span class="updated">
                    ${this._hasReceivers?s?Ps(s)===$e("rel.just_now")?$e("mirror.last_send_just"):$e("mirror.last_send_ago",{rel:Ps(s)}):"":$e("mirror.no_receivers")}
                </span>
            </div>
        `}_renderToolbar(e){const t=e.filter(e=>0===(e.sig.heard_by??[]).length).length,i=new Map;for(const t of e)for(const e of t.emitters)i.set(e,(i.get(e)??0)+1);return F`
            <div class="toolbar">
                <button
                    class="fchip ${"all"===this._filter?"on":""}"
                    @click=${()=>this._filter="all"}
                >
                    ${$e("mirror.filter_all",{count:e.length})}
                </button>
                ${this._hasReceivers?F`
                          <button
                              class="fchip warnc ${"notheard"===this._filter?"on":""}"
                              @click=${()=>this._filter="notheard"}
                          >
                              ${$e("mirror.filter_not_heard",{count:t})}
                          </button>
                      `:""}
                ${[...i.entries()].map(([e,t])=>F`
                        <button
                            class="fchip ${this._filter===e?"on":""}"
                            @click=${()=>this._filter=e}
                        >
                            ${e} (${t})
                        </button>
                    `)}
                <input
                    class="search"
                    type="text"
                    placeholder=${$e("mirror.search")}
                    .value=${this._search}
                    @input=${e=>{this._search=e.target.value}}
                />
            </div>
        `}_renderRow(e){const t=e.sig,i=this._bloomIds.has(t.id),s=!!t.code,r=this._testingSignalId===t.id;return F`
            <div class="mrow ${i?"bloom":""}">
                <div class="mrow-main">
                    <div class="mrow-title">
                        <span class="name">${e.title}</span>
                        ${e.pill?F`<span
                                  class="pill ${e.pillRaw?"raw":""}"
                                  >${e.pill}</span
                              >`:""}
                        ${(t.send_count??1)>1?F`<span
                                  class="repeat-indicator"
                                  title=${$e("mirror.sends_times",{count:t.send_count})}
                                  ><ha-svg-icon
                                      .path=${"M17,17H7V14L3,18L7,22V19H19V13H17M7,7H17V10L21,6L17,2V5H5V11H7V7Z"}
                                  ></ha-svg-icon
                                  >${t.send_count}</span
                              >`:""}
                        ${(t.repeat_count??1)>1&&t.decoded_protocol?F`<span
                                  class="ditto-indicator"
                                  title=${$e("cmdrow.dittos",{count:t.repeat_count})}
                                  ><ha-svg-icon
                                      .path=${"M16,12A2,2 0 0,1 18,10A2,2 0 0,1 20,12A2,2 0 0,1 18,14A2,2 0 0,1 16,12M10,12A2,2 0 0,1 12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12M4,12A2,2 0 0,1 6,10A2,2 0 0,1 8,12A2,2 0 0,1 6,14A2,2 0 0,1 4,12Z"}
                                  ></ha-svg-icon
                                  >${t.repeat_count}</span
                              >`:""}
                    </div>
                    ${e.unknownSend?F`
                              <div class="mrow-hint">
                                  ${$e("mirror.unknown_hint").split("{name}")[0]}<em
                                      class="hint-emitter"
                                      >${e.emitters[0]??$e("mirror.the_blaster")}</em
                                  >${$e("mirror.unknown_hint").split("{name}")[1]??""}
                              </div>
                          `:F`
                              <div class="mrow-sub">
                                  ${e.via?F`<span title=${e.viaFull}
                                            >${e.via}</span
                                        >`:""}
                                  ${null!==e.heard?F`
                                            <span class="arrow"
                                                >&#10142;</span
                                            >
                                            <span
                                                class=${e.heardOk?"heard":"not-heard"}
                                                >${e.heard}</span
                                            >
                                        `:""}
                                  <span class="src-chip">${e.chip}</span>
                              </div>
                          `}
                </div>
                <div class="mrow-meta">
                    <span class="counts"
                        >${t.hit_count}
                        ${1===t.hit_count?"send":"sends"}${t.last_seen?F` &middot; ${Ps(t.last_seen)}`:""}</span
                    >
                    ${t.code?F`
                              <button
                                  class="code-btn"
                                  title=${$e("cmdrow.edit_code")}
                                  @click=${e=>{e.stopPropagation(),this._editSignal=t}}
                              >
                                  <ha-svg-icon
                                      .path=${"M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"}
                                      style="--mdc-icon-size:10px"
                                  ></ha-svg-icon>
                              </button>
                          `:""}
                    <button
                        class="action-btn assign-btn"
                        ?disabled=${!s}
                        title=${s?t.assignment_count&&t.assigned_to?.length?1===t.assignment_count?$e("mirror.assigned_one",{device:t.assigned_to[0].device_name,command:t.assigned_to[0].command_name}):$e("mirror.assigned_n",{count:t.assignment_count})+`\n- ${t.assigned_to.map(e=>`${e.device_name} / ${e.command_name}`).join("\n- ")}`:$e("mirror.assign_title"):$e("mirror.assign_disabled")}
                        @click=${e=>{e.stopPropagation(),this._onAssignClick(t,e)}}
                    >${$e("assign.assign")}<ir-count-dot
                            color="green"
                            .count=${t.assignment_count??0}
                        ></ir-count-dot></button>
                    <button
                        class="action-btn test-btn"
                        ?disabled=${!s||r}
                        title=${$e(s?"mirror.test_title":"mirror.test_disabled")}
                        @click=${e=>{e.stopPropagation(),this._testDialog=t}}
                    >${r?this._testResult??$e("mirror.sending"):$e("mirror.test")}</button>
                    <button
                        class="action-btn trigger-btn"
                        ?disabled=${!s}
                        title=${s?this._triggerCountFor(t)>0?$e("mirror.trigger_edit"):$e("mirror.trigger_create"):$e("mirror.trigger_disabled")}
                        @click=${e=>{e.stopPropagation(),this._openTriggerDialog(t,e)}}
                    >${$e("cmdrow.trigger")}<ir-count-dot
                            color="yellow"
                            .count=${this._triggerCountFor(t)}
                        ></ir-count-dot></button>
                    <button
                        class="action-btn delete-btn"
                        title=${$e("mirror.delete_title")}
                        @click=${e=>{e.stopPropagation(),this._deleteSignal=t}}
                    >${$e("common.delete")}</button>
                </div>
            </div>
        `}_renderEmpty(){return F`
            <div class="empty">
                <ha-svg-icon
                    class="empty-icon"
                    .path=${Rs}
                ></ha-svg-icon>
                <div class="empty-title">${$e("mirror.empty_title")}</div>
                <div class="empty-sub">
                    ${$e("mirror.empty_sub")}
                </div>
            </div>
        `}_renderDialogs(){return F`
            ${this._triggerPopover?F`<ir-trigger-popover
                      .triggers=${this._triggers.filter(e=>_s(e,this._triggerPopover.signal))}
                      .receivers=${this._receivers}
                      .top=${this._triggerPopover.top}
                      .left=${this._triggerPopover.left}
                      @create-new=${this._onPopoverCreateNew}
                      @edit-trigger=${this._onPopoverEditTrigger}
                  ></ir-trigger-popover>`:""}
            ${this._assignedPopover?F`<ir-assigned-popover
                      .assignments=${this._assignedPopover.signal.assigned_to??[]}
                      .top=${this._assignedPopover.top}
                      .left=${this._assignedPopover.left}
                      @create-new=${this._onAssignedPopoverCreateNew}
                      @open-assignment=${this._onAssignedPopoverOpen}
                  ></ir-assigned-popover>`:""}
            ${this._triggerDialog?F`<ir-trigger-dialog
                      .api=${this.api}
                      .signalFingerprint=${this._triggerDialog.fingerprint}
                      .byteHash=${this._triggerDialog.byte_hash??null}
                      .decodedFingerprint=${this._triggerDialog.decoded_fingerprint??null}
                      .protocol=${this._triggerDialog.protocol}
                      .code=${this._triggerDialog.code}
                      .slPattern=${this._triggerDialog.sl_pattern??null}
                      .alias=${this._triggerDialog.alias||null}
                      .mirrorContext=${!0}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                  ></ir-trigger-dialog>`:""}
            ${this._triggerEditDialog?F`<ir-trigger-dialog
                      .api=${this.api}
                      .trigger=${this._triggerEditDialog}
                      .mirrorContext=${!0}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                      @trigger-delete=${e=>this._requestDeleteTrigger(e.detail.triggerId)}
                  ></ir-trigger-dialog>`:""}
            ${this._confirmDeleteTriggerId?F`<ir-confirm-dialog
                      title=${$e("mirror.del_trigger_title")}
                      message=${$e("mirror.del_trigger_msg")}
                      confirmLabel=${$e("common.delete")}
                      .destructive=${!0}
                      @confirmed=${this._confirmDeleteTrigger}
                      @closed=${()=>this._confirmDeleteTriggerId=null}
                  ></ir-confirm-dialog>`:""}
            ${this._deleteSignal?F`<ir-confirm-dialog
                      title=${$e("mirror.clear_title")}
                      message=${$e("mirror.clear_msg")}
                      confirmLabel=${$e("common.delete")}
                      .destructive=${!0}
                      @confirmed=${this._confirmDeleteSignal}
                      @closed=${()=>this._deleteSignal=null}
                  ></ir-confirm-dialog>`:""}
            ${this._assignSignal&&this._device?F`<ir-assign-signal-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .unknownDeviceId=${this._device.id}
                      .signal=${this._assignSignal.signal}
                      .suggestedDeviceName=${""}
                      .initialMode=${this._assignSignal.initialMode}
                      @signal-assigned=${this._onSignalAssigned}
                      @closed=${()=>this._assignSignal=null}
                  ></ir-assign-signal-dialog>`:""}
            ${this._editSignal&&this._device?F`<ir-signal-editor
                      .api=${this.api}
                      .deviceId=${this._device.id}
                      .signalId=${this._editSignal.id}
                      .initialPronto=${this._editSignal.code??""}
                      .initialAlias=${this._editSignal.alias??""}
                      .initialSendCount=${this._editSignal.send_count??1}
                      .initialDitto=${this._editSignal.repeat_count??1}
                      .initialObservedRepeatCount=${this._editSignal.observed_repeat_count??0}
                      .hasTrigger=${this._triggerCountFor(this._editSignal)>0}
                      @signal-edited=${this._onSignalEdited}
                      @closed=${()=>this._editSignal=null}
                  ></ir-signal-editor>`:""}
            ${this._testDialog?F`<ir-test-emitter-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .value=${this._testEmitters}
                      @emitters-changed=${e=>this._testEmitters=e.detail.value}
                      @send=${this._sendTest}
                      @closed=${()=>this._testDialog=null}
                  ></ir-test-emitter-dialog>`:""}
        `}};Ms.styles=[Vi,a`
            :host {
                display: block;
            }
            .loading,
            .no-match {
                text-align: center;
                color: var(--secondary-text-color);
                padding: 24px;
            }

            /* Tab header, same anatomy as the Sniffer/Clipper/Plucker
               titles; the mirror icon wears the tab's silver. */
            .tab-head {
                display: flex;
                align-items: center;
                margin-bottom: 12px;
            }
            .title {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 1.1rem;
                font-weight: 500;
                color: var(--primary-text-color);
            }
            .title ha-svg-icon {
                --mdc-icon-size: 24px;
                color: #607d8b;
            }
            .title .count {
                font-size: 0.85rem;
                font-weight: 400;
                color: var(--secondary-text-color);
            }
            .error {
                color: var(--error-color, #db4437);
                padding: 8px 0;
            }

            /* Stats strip: the silver sheen lives here, as texture.
               Deliberately slim (owner bench note: less air above and
               below) -- values and labels sit on one line per stat. */
            .stats {
                display: flex;
                align-items: baseline;
                gap: 22px;
                background: var(--secondary-background-color);
                border: 1px solid var(--divider-color);
                border-radius: 8px;
                padding: 6px 14px;
                margin-bottom: 12px;
                background-image: linear-gradient(
                    105deg,
                    transparent 42%,
                    rgba(144, 164, 174, 0.12) 50%,
                    transparent 58%
                );
            }
            .stat {
                display: flex;
                align-items: baseline;
                gap: 5px;
            }
            .stat .v {
                font-size: 15px;
                font-weight: 600;
                color: var(--primary-text-color);
            }
            .stat .l {
                font-size: 10.5px;
                color: var(--secondary-text-color);
                letter-spacing: 0.4px;
            }
            .stat .v.warn {
                color: #e65100;
            }
            .stats .updated {
                margin-left: auto;
                font-size: 11.5px;
                color: var(--secondary-text-color);
            }

            /* Toolbar */
            .toolbar {
                display: flex;
                gap: 8px;
                align-items: center;
                margin-bottom: 14px;
                flex-wrap: wrap;
            }
            .fchip {
                font-size: 12.5px;
                padding: 5px 13px;
                border-radius: 16px;
                border: 1px solid var(--divider-color);
                background: var(--card-background-color);
                color: var(--secondary-text-color);
                font-family: inherit;
                cursor: pointer;
            }
            .fchip.on {
                background: #607d8b;
                border-color: #607d8b;
                color: #fff;
            }
            .fchip.warnc:not(.on) {
                color: #e65100;
                border-color: #ffcf9e;
            }
            .search {
                flex: 1 1 180px;
                border: 1px solid var(--divider-color);
                border-radius: 8px;
                padding: 6px 12px;
                font-size: 13px;
                font-family: inherit;
                background: var(--card-background-color);
                color: var(--primary-text-color);
            }
            .search:focus {
                outline: none;
                border-color: #607d8b;
            }

            /* Rows: each send is its own rounded card (owner bench note),
               matching the card language of the Devices, Sniffer, and
               Clipper surfaces instead of a welded table. */
            .rows {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            .mrow {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 10px 16px;
                border: 1px solid var(--divider-color);
                border-radius: 10px;
                background: var(--card-background-color);
                /* Carries the soft exit after the bloom class drops --
                   same durations as the trigger card. */
                transition: box-shadow 300ms ease, border-color 300ms ease,
                            background 400ms ease;
            }
            .mrow:hover {
                background: var(--secondary-background-color);
            }
            /* The silver bloom a send makes while you watch: the WHOLE
               card glows and fades (owner bench note -- the old left-edge
               chip read as a sliver). Lifecycle is the trigger card's,
               verbatim, in silver: the animation fades to nothing over
               2.4s, the class's static styles snap back for one last
               pass (class held to 2500ms, see BLOOM_MS), then the class
               drops and the row's transitions carry the soft exit. */
            .mrow.bloom {
                border-color: #90a4ae;
                background: rgba(144, 164, 174, 0.08);
                animation: mirror-bloom 2.4s ease-out;
            }
            @keyframes mirror-bloom {
                0% {
                    background: rgba(144, 164, 174, 0.18);
                    border-color: #b0bec5;
                    box-shadow: 0 0 16px 4px rgba(144, 164, 174, 0.4);
                }
                30% {
                    background: rgba(144, 164, 174, 0.1);
                    border-color: #90a4ae;
                    box-shadow: 0 0 8px 2px rgba(144, 164, 174, 0.2);
                }
                60% {
                    background: rgba(144, 164, 174, 0.06);
                    box-shadow: 0 0 4px 1px rgba(144, 164, 174, 0.1);
                }
                100% {
                    background: transparent;
                    border-color: var(--divider-color);
                    box-shadow: none;
                }
            }
            .mrow-main {
                min-width: 0;
            }
            .mrow-title {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 14px;
            }
            .mrow-title .name {
                font-weight: 500;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            .pill {
                font-size: 10px;
                letter-spacing: 0.4px;
                font-weight: 500;
                padding: 2px 7px;
                border-radius: 9px;
                background: rgba(33, 150, 243, 0.12);
                color: #1565c0;
                white-space: nowrap;
            }
            .pill.raw {
                background: rgba(230, 140, 60, 0.12);
                color: #b87333;
            }
            /* TX-knob indicators, same anatomy as the command rows'. */
            .repeat-indicator,
            .ditto-indicator {
                display: inline-flex;
                align-items: center;
                gap: 1px;
                font-size: 9px;
                font-weight: 600;
                opacity: 0.85;
            }
            .repeat-indicator {
                color: var(--warning-color, #ff9800);
            }
            .ditto-indicator {
                color: var(--primary-color);
            }
            .repeat-indicator ha-svg-icon,
            .ditto-indicator ha-svg-icon {
                --mdc-icon-size: 10px;
            }
            .mrow-sub {
                margin-top: 4px;
                font-size: 12px;
                color: var(--secondary-text-color);
                display: flex;
                align-items: center;
                gap: 6px;
                flex-wrap: wrap;
            }
            /* Unknown-send explanation: replaces the whole sub-line on
               foreign never-heard rows (owner wording). Plain prose, so
               it wraps like a sentence rather than flexing like chips. */
            .mrow-hint {
                margin-top: 4px;
                font-size: 12px;
                color: var(--secondary-text-color);
                line-height: 1.45;
                max-width: 46em;
            }
            /* The emitter's name reads as part of the sentence without
               a marker (owner bench note); italic says "this is YOUR
               device's name, not our words." */
            .mrow-hint .hint-emitter {
                font-style: italic;
            }
            .arrow {
                color: #b0bec5;
            }
            .heard {
                color: #2e7d32;
            }
            /* Neutral grey, not amber: one-way homes are normal. */
            .not-heard {
                color: #90a4ae;
            }
            .src-chip {
                font-size: 10.5px;
                padding: 1px 8px;
                border-radius: 8px;
                background: rgba(96, 125, 139, 0.12);
                color: #546e7a;
                white-space: nowrap;
            }
            .mrow-meta {
                margin-left: auto;
                display: flex;
                align-items: center;
                gap: 10px;
                white-space: nowrap;
            }
            .counts {
                font-size: 12px;
                color: var(--secondary-text-color);
            }
            .code-btn {
                background: none;
                border: none;
                cursor: pointer;
                color: var(--secondary-text-color);
                padding: 2px;
                display: inline-flex;
                align-items: center;
            }

            /* Empty state: the feature explaining itself. */
            .empty {
                text-align: center;
                padding: 44px 20px 52px;
            }
            .empty-icon {
                --mdc-icon-size: 44px;
                color: #607d8b;
                margin-bottom: 12px;
            }
            .empty-title {
                font-size: 15px;
                font-weight: 500;
                color: var(--primary-text-color);
            }
            .empty-sub {
                font-size: 12.5px;
                color: var(--secondary-text-color);
                margin-top: 6px;
                max-width: 420px;
                margin-left: auto;
                margin-right: auto;
                line-height: 1.5;
            }
        `],e([pe({attribute:!1})],Ms.prototype,"api",void 0),e([pe({attribute:!1})],Ms.prototype,"hass",void 0),e([he()],Ms.prototype,"_device",void 0),e([he()],Ms.prototype,"_loading",void 0),e([he()],Ms.prototype,"_error",void 0),e([he()],Ms.prototype,"_triggers",void 0),e([he()],Ms.prototype,"_receivers",void 0),e([he()],Ms.prototype,"_hasReceivers",void 0),e([he()],Ms.prototype,"_filter",void 0),e([he()],Ms.prototype,"_search",void 0),e([he()],Ms.prototype,"_bloomIds",void 0),e([he()],Ms.prototype,"_assignSignal",void 0),e([he()],Ms.prototype,"_assignedPopover",void 0),e([he()],Ms.prototype,"_triggerDialog",void 0),e([he()],Ms.prototype,"_triggerEditDialog",void 0),e([he()],Ms.prototype,"_triggerPopover",void 0),e([he()],Ms.prototype,"_confirmDeleteTriggerId",void 0),e([he()],Ms.prototype,"_deleteSignal",void 0),e([he()],Ms.prototype,"_editSignal",void 0),e([he()],Ms.prototype,"_testDialog",void 0),e([he()],Ms.prototype,"_testEmitters",void 0),e([he()],Ms.prototype,"_testingSignalId",void 0),e([he()],Ms.prototype,"_testResult",void 0),Ms=e([me("ir-mirror")],Ms);let Hs=class extends ne{constructor(){super(...arguments),this.narrow=!1,this._activeTab="devices",this._devices=[],this._expandedDeviceId=null,this._loading=!0,this._error=null,this._addDialogOpen=!1,this._pluckersAvailable=!1,this._pendingPluckEntity="",this._api=null}connectedCallback(){super.connectedCallback(),this.hass&&this._init()}updated(e){e.has("hass")&&this.hass&&(function(e){const t=e||"en";if(t!==fe){fe=t;try{ye=new Intl.PluralRules(t)}catch{ye=new Intl.PluralRules("en")}}const i=t.toLowerCase();let s="en";if(ve[i])s=i;else{const e=i.split("-")[0];ve[e]&&(s=e)}be=s}(this.hass.language),this._api||this._init())}_init(){this._api=new ue(this.hass),this._refreshDevices(),this._checkPluckers()}async _checkPluckers(){if(this._api){try{const{vendors:e}=await this._api.listPluckVendors();this._pluckersAvailable=e.length>0}catch{this._pluckersAvailable=!1}"plucker"!==this._activeTab||this._pluckersAvailable||this._switchTab("devices")}}_tagline(){return $e(`panel.tagline.${this._activeTab}`)}async _refreshDevices(){if(this._api){this._loading=!0;try{this._devices=await this._api.listDevices(),this._error=null}catch(e){this._error=$e("panel.load_failed",{message:e.message})}finally{this._loading=!1}}}_toggleDevice(e){this._expandedDeviceId=this._expandedDeviceId===e?null:e}_openAddDialog(){this._addDialogOpen=!0}_onNavigatePlucker(e){this._pendingPluckEntity=e.detail?.vendor_entity_id??"",this._switchTab("plucker")}_onNavigateDevice(e){this._switchTab("devices"),this._expandedDeviceId=e.detail}_closeAddDialog(){this._addDialogOpen=!1}async _onDeviceCreated(e){this._addDialogOpen=!1,await this._refreshDevices(),this._expandedDeviceId=e.detail.id}async _onDeviceChanged(){await this._refreshDevices()}async _onDeviceDeleted(){this._expandedDeviceId=null,await this._refreshDevices()}_switchTab(e){this._expandedDeviceId=null,this._activeTab=e,"devices"===e&&this._refreshDevices()}_openHaSidebar(){this.dispatchEvent(new Event("hass-toggle-menu",{bubbles:!0,composed:!0}))}render(){return this._api?F`
            <ha-top-app-bar-fixed>
                <ha-menu-button
                    slot="navigationIcon"
                    .hass=${this.hass}
                ></ha-menu-button>

            <div class="mobile-nav-row">
                <button
                    class="mobile-nav-button"
                    title=${$e("panel.open_menu")}
                    aria-label=${$e("panel.open_menu")}
                    @click=${this._openHaSidebar}
                >
                    <ha-svg-icon
                        .path=${"M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z"}
                    ></ha-svg-icon>
                </button>
            </div>

            <div class="header-banner">
                <img
                    src="/hair_panel/assets/hair-header.png"
                    alt="HAIR"
                    class="header-img"
                />
            </div>

            <div class="tab-bar">
                <button
                    class="tab ${"devices"===this._activeTab?"active":""}"
                    @click=${()=>this._switchTab("devices")}
                >
                    ${$e("panel.tab.devices")}
                </button>
                <button
                    class="tab ${"sniffer"===this._activeTab?"active":""}"
                    @click=${()=>this._switchTab("sniffer")}
                >
                    Sniffer
                </button>
                <button
                    class="tab ${"clips"===this._activeTab?"active":""}"
                    @click=${()=>this._switchTab("clips")}
                >
                    Clipper
                </button>
                ${this._pluckersAvailable?F`<button
                          class="tab ${"plucker"===this._activeTab?"active":""}"
                          @click=${()=>this._switchTab("plucker")}
                      >
                          Plucker
                      </button>`:""}
                <button
                    class="tab mirror-tab ${"mirror"===this._activeTab?"active":""}"
                    @click=${()=>this._switchTab("mirror")}
                >
                    Mirror
                </button>
            </div>

            <div class="tab-tagline">${this._tagline()}</div>

            <div class="content">
                ${this._error?F`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}
                ${"devices"===this._activeTab?F`
                          <ir-device-list
                              .devices=${this._devices}
                              .hass=${this.hass}
                              .api=${this._api}
                              .loading=${this._loading}
                              .expandedDeviceId=${this._expandedDeviceId}
                              @device-selected=${e=>this._toggleDevice(e.detail)}
                              @device-changed=${this._onDeviceChanged}
                              @device-deleted=${this._onDeviceDeleted}
                              @navigate-sniffer=${()=>this._switchTab("sniffer")}
                              @navigate-clips=${()=>this._switchTab("clips")}
                              @navigate-mirror=${()=>this._switchTab("mirror")}
                              @navigate-plucker=${this._onNavigatePlucker}
                              @add-device=${this._openAddDialog}
                          ></ir-device-list>

                      `:"sniffer"===this._activeTab?F`
                            <ir-signal-monitor
                                .api=${this._api}
                                .hass=${this.hass}
                                @navigate-device=${this._onNavigateDevice}
                            ></ir-signal-monitor>
                        `:"clips"===this._activeTab?F`
                              <ir-clips
                                  .api=${this._api}
                                  .hass=${this.hass}
                                  @navigate-device=${this._onNavigateDevice}
                              ></ir-clips>
                          `:"plucker"===this._activeTab?F`
                                <ir-pluck
                                    .api=${this._api}
                                    .hass=${this.hass}
                                    .pendingEntity=${this._pendingPluckEntity}
                                    @navigate-device=${this._onNavigateDevice}
                                ></ir-pluck>
                            `:F`
                                <ir-mirror
                                    .api=${this._api}
                                    .hass=${this.hass}
                                    @navigate-device=${this._onNavigateDevice}
                                ></ir-mirror>
                            `}
            </div>

            ${this._addDialogOpen?F`
                      <ir-add-device-dialog
                          .api=${this._api}
                          .hass=${this.hass}
                          @closed=${this._closeAddDialog}
                          @device-created=${this._onDeviceCreated}
                      ></ir-add-device-dialog>
                  `:""}

            <div class="version-footer">v${"0.6.7"}</div>
            </ha-top-app-bar-fixed>
        `:F`<div class="loading">${$e("panel.loading")}</div>`}};Hs.styles=a`
        :host {
            display: block;
            background: var(--primary-background-color);
            color: var(--primary-text-color);
            min-height: 100vh;
        }
        .version-footer {
            text-align: center;
            color: var(--secondary-text-color);
            opacity: 0.5;
            font-size: 12px;
            padding: 24px 0 16px;
        }
        .header-banner {
            max-width: 1100px;
            margin: 0 auto;
            padding: 12px 16px 0;
            text-align: center;
        }
        .header-img {
            max-width: 100%;
            height: auto;
            max-height: 120px;
            object-fit: contain;
            border-radius: 6px;
        }
        .tab-tagline {
            max-width: 1100px;
            margin: 0 auto;
            padding: 8px 16px 0;
            font-size: 0.82rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            text-align: center;
            color: var(--secondary-text-color);
        }
        .tab-bar {
            display: flex;
            align-items: center;
            border-bottom: 1px solid var(--divider-color);
            padding: 0 16px;
            max-width: 1100px;
            margin: 0 auto;
        }
        .tab-spacer {
            flex: 1;
        }
        .add-device-btn {
            display: flex;
            align-items: center;
            gap: 6px;
            background: none;
            color: var(--primary-color);
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 0.75rem;
            font-weight: 500;
            cursor: pointer;
            font-family: inherit;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            transition: background 150ms ease;
        }
        .add-device-btn:hover {
            background: var(--secondary-background-color);
        }
        /* Clipper's tab-bar create button: identical to Add Device (gray
           stroke, neutral hover), just with copper text + icon. */
        .clipper-create-btn {
            color: #b87333;
        }
        .add-device-btn ha-svg-icon {
            --mdc-icon-size: 14px;
        }
        .tab {
            background: none;
            border: none;
            border-bottom: 2px solid transparent;
            padding: 12px 20px;
            font-size: 0.9rem;
            font-weight: 500;
            color: var(--secondary-text-color);
            cursor: pointer;
            transition: color 150ms ease, border-color 150ms ease;
            font-family: inherit;
        }
        .tab:hover {
            color: var(--primary-text-color);
        }
        .tab.active {
            color: var(--primary-color);
            border-bottom-color: var(--primary-color);
        }
        /* The Mirror wears silver (v0.6.6), matching its tab accent. */
        .tab.mirror-tab.active {
            color: #607d8b;
            border-bottom-color: #607d8b;
        }
        .content {
            padding: 16px;
            max-width: 1100px;
            margin: 0 auto;
        }
        .loading {
            padding: 48px;
            text-align: center;
            color: var(--secondary-text-color);
        }

        /* Mobile-only navigation row.
           Custom HA panels can have their system header hidden by the
           parent shell on the HA Companion app, especially on iOS where
           swipe-to-go-back does not exist as a platform gesture. Adding
           a hamburger inside the panel content guarantees mobile users
           always have a visible nav target. Hidden on desktop because
           the ha-top-app-bar-fixed above already exposes the same menu
           button there, and a second control would be redundant. */
        .mobile-nav-row {
            display: none;
        }
        @media (max-width: 768px) {
            .mobile-nav-row {
                display: flex;
                align-items: center;
                padding: 8px 12px 0;
                max-width: 1100px;
                margin: 0 auto;
            }
        }
        .mobile-nav-button {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            color: var(--secondary-text-color);
            padding: 6px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            transition: background 150ms ease, color 150ms ease;
        }
        .mobile-nav-button:hover {
            background: var(--secondary-background-color);
            color: var(--primary-text-color);
        }
        .mobile-nav-button ha-svg-icon {
            --mdc-icon-size: 22px;
        }
    `,e([pe({attribute:!1})],Hs.prototype,"hass",void 0),e([pe({attribute:!1})],Hs.prototype,"narrow",void 0),e([pe({attribute:!1})],Hs.prototype,"route",void 0),e([pe({attribute:!1})],Hs.prototype,"panel",void 0),e([he()],Hs.prototype,"_activeTab",void 0),e([he()],Hs.prototype,"_devices",void 0),e([he()],Hs.prototype,"_expandedDeviceId",void 0),e([he()],Hs.prototype,"_loading",void 0),e([he()],Hs.prototype,"_error",void 0),e([he()],Hs.prototype,"_addDialogOpen",void 0),e([he()],Hs.prototype,"_pluckersAvailable",void 0),e([he()],Hs.prototype,"_pendingPluckEntity",void 0),Hs=e([me("ha-panel-ir-devices")],Hs);export{Hs as HaPanelIrDevices};
