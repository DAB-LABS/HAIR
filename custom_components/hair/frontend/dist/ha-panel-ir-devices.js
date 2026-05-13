function e(e,t,i,s){var a,o=arguments.length,n=o<3?t:null===s?s=Object.getOwnPropertyDescriptor(t,i):s;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)n=Reflect.decorate(e,t,i,s);else for(var r=e.length-1;r>=0;r--)(a=e[r])&&(n=(o<3?a(n):o>3?a(t,i,n):a(t,i))||n);return o>3&&n&&Object.defineProperty(t,i,n),n}"function"==typeof SuppressedError&&SuppressedError;const t=globalThis,i=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,s=Symbol(),a=new WeakMap;let o=class{constructor(e,t,i){if(this._$cssResult$=!0,i!==s)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(i&&void 0===e){const i=void 0!==t&&1===t.length;i&&(e=a.get(t)),void 0===e&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),i&&a.set(t,e))}return e}toString(){return this.cssText}};const n=(e,...t)=>{const i=1===e.length?e[0]:t.reduce((t,i,s)=>t+(e=>{if(!0===e._$cssResult$)return e.cssText;if("number"==typeof e)return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+e[s+1],e[0]);return new o(i,e,s)},r=i?e=>e:e=>e instanceof CSSStyleSheet?(e=>{let t="";for(const i of e.cssRules)t+=i.cssText;return(e=>new o("string"==typeof e?e:e+"",void 0,s))(t)})(e):e,{is:d,defineProperty:c,getOwnPropertyDescriptor:l,getOwnPropertyNames:h,getOwnPropertySymbols:p,getPrototypeOf:u}=Object,v=globalThis,m=v.trustedTypes,_=m?m.emptyScript:"",g=v.reactiveElementPolyfillSupport,b=(e,t)=>e,y={toAttribute(e,t){switch(t){case Boolean:e=e?_:null;break;case Object:case Array:e=null==e?e:JSON.stringify(e)}return e},fromAttribute(e,t){let i=e;switch(t){case Boolean:i=null!==e;break;case Number:i=null===e?null:Number(e);break;case Object:case Array:try{i=JSON.parse(e)}catch(e){i=null}}return i}},f=(e,t)=>!d(e,t),$={attribute:!0,type:String,converter:y,reflect:!1,useDefault:!1,hasChanged:f};Symbol.metadata??=Symbol("metadata"),v.litPropertyMetadata??=new WeakMap;let x=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=$){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const i=Symbol(),s=this.getPropertyDescriptor(e,i,t);void 0!==s&&c(this.prototype,e,s)}}static getPropertyDescriptor(e,t,i){const{get:s,set:a}=l(this.prototype,e)??{get(){return this[t]},set(e){this[t]=e}};return{get:s,set(t){const o=s?.call(this);a?.call(this,t),this.requestUpdate(e,o,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??$}static _$Ei(){if(this.hasOwnProperty(b("elementProperties")))return;const e=u(this);e.finalize(),void 0!==e.l&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(b("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(b("properties"))){const e=this.properties,t=[...h(e),...p(e)];for(const i of t)this.createProperty(i,e[i])}const e=this[Symbol.metadata];if(null!==e){const t=litPropertyMetadata.get(e);if(void 0!==t)for(const[e,i]of t)this.elementProperties.set(e,i)}this._$Eh=new Map;for(const[e,t]of this.elementProperties){const i=this._$Eu(e,t);void 0!==i&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const i=new Set(e.flat(1/0).reverse());for(const e of i)t.unshift(r(e))}else void 0!==e&&t.push(r(e));return t}static _$Eu(e,t){const i=t.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof e?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),void 0!==this.renderRoot&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const i of t.keys())this.hasOwnProperty(i)&&(e.set(i,this[i]),delete this[i]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((e,s)=>{if(i)e.adoptedStyleSheets=s.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(const i of s){const s=document.createElement("style"),a=t.litNonce;void 0!==a&&s.setAttribute("nonce",a),s.textContent=i.cssText,e.appendChild(s)}})(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,i){this._$AK(e,i)}_$ET(e,t){const i=this.constructor.elementProperties.get(e),s=this.constructor._$Eu(e,i);if(void 0!==s&&!0===i.reflect){const a=(void 0!==i.converter?.toAttribute?i.converter:y).toAttribute(t,i.type);this._$Em=e,null==a?this.removeAttribute(s):this.setAttribute(s,a),this._$Em=null}}_$AK(e,t){const i=this.constructor,s=i._$Eh.get(e);if(void 0!==s&&this._$Em!==s){const e=i.getPropertyOptions(s),a="function"==typeof e.converter?{fromAttribute:e.converter}:void 0!==e.converter?.fromAttribute?e.converter:y;this._$Em=s;const o=a.fromAttribute(t,e.type);this[s]=o??this._$Ej?.get(s)??o,this._$Em=null}}requestUpdate(e,t,i,s=!1,a){if(void 0!==e){const o=this.constructor;if(!1===s&&(a=this[e]),i??=o.getPropertyOptions(e),!((i.hasChanged??f)(a,t)||i.useDefault&&i.reflect&&a===this._$Ej?.get(e)&&!this.hasAttribute(o._$Eu(e,i))))return;this.C(e,t,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(e,t,{useDefault:i,reflect:s,wrapped:a},o){i&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,o??t??this[e]),!0!==a||void 0!==o)||(this._$AL.has(e)||(this.hasUpdated||i||(t=void 0),this._$AL.set(e,t)),!0===s&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}const e=this.scheduleUpdate();return null!=e&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[e,t]of this._$Ep)this[e]=t;this._$Ep=void 0}const e=this.constructor.elementProperties;if(e.size>0)for(const[t,i]of e){const{wrapped:e}=i,s=this[t];!0!==e||this._$AL.has(t)||void 0===s||this.C(t,void 0,i,s)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(e=>e.hostUpdate?.()),this.update(t)):this._$EM()}catch(t){throw e=!1,this._$EM(),t}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(e){}firstUpdated(e){}};x.elementStyles=[],x.shadowRootOptions={mode:"open"},x[b("elementProperties")]=new Map,x[b("finalized")]=new Map,g?.({ReactiveElement:x}),(v.reactiveElementVersions??=[]).push("2.1.2");const w=globalThis,C=e=>e,k=w.trustedTypes,D=k?k.createPolicy("lit-html",{createHTML:e=>e}):void 0,A="$lit$",E=`lit$${Math.random().toFixed(9).slice(2)}$`,S="?"+E,I=`<${S}>`,P=document,N=()=>P.createComment(""),T=e=>null===e||"object"!=typeof e&&"function"!=typeof e,M=Array.isArray,R="[ \t\n\f\r]",H=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,L=/-->/g,z=/>/g,U=RegExp(`>|${R}(?:([^\\s"'>=/]+)(${R}*=${R}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),O=/'/g,V=/"/g,j=/^(?:script|style|textarea|title)$/i,F=(e,...t)=>({_$litType$:1,strings:e,values:t}),q=Symbol.for("lit-noChange"),B=Symbol.for("lit-nothing"),Z=new WeakMap,W=P.createTreeWalker(P,129);function X(e,t){if(!M(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==D?D.createHTML(t):t}const K=(e,t)=>{const i=e.length-1,s=[];let a,o=2===t?"<svg>":3===t?"<math>":"",n=H;for(let t=0;t<i;t++){const i=e[t];let r,d,c=-1,l=0;for(;l<i.length&&(n.lastIndex=l,d=n.exec(i),null!==d);)l=n.lastIndex,n===H?"!--"===d[1]?n=L:void 0!==d[1]?n=z:void 0!==d[2]?(j.test(d[2])&&(a=RegExp("</"+d[2],"g")),n=U):void 0!==d[3]&&(n=U):n===U?">"===d[0]?(n=a??H,c=-1):void 0===d[1]?c=-2:(c=n.lastIndex-d[2].length,r=d[1],n=void 0===d[3]?U:'"'===d[3]?V:O):n===V||n===O?n=U:n===L||n===z?n=H:(n=U,a=void 0);const h=n===U&&e[t+1].startsWith("/>")?" ":"";o+=n===H?i+I:c>=0?(s.push(r),i.slice(0,c)+A+i.slice(c)+E+h):i+E+(-2===c?t:h)}return[X(e,o+(e[i]||"<?>")+(2===t?"</svg>":3===t?"</math>":"")),s]};class Y{constructor({strings:e,_$litType$:t},i){let s;this.parts=[];let a=0,o=0;const n=e.length-1,r=this.parts,[d,c]=K(e,t);if(this.el=Y.createElement(d,i),W.currentNode=this.el.content,2===t||3===t){const e=this.el.content.firstChild;e.replaceWith(...e.childNodes)}for(;null!==(s=W.nextNode())&&r.length<n;){if(1===s.nodeType){if(s.hasAttributes())for(const e of s.getAttributeNames())if(e.endsWith(A)){const t=c[o++],i=s.getAttribute(e).split(E),n=/([.?@])?(.*)/.exec(t);r.push({type:1,index:a,name:n[2],strings:i,ctor:"."===n[1]?te:"?"===n[1]?ie:"@"===n[1]?se:ee}),s.removeAttribute(e)}else e.startsWith(E)&&(r.push({type:6,index:a}),s.removeAttribute(e));if(j.test(s.tagName)){const e=s.textContent.split(E),t=e.length-1;if(t>0){s.textContent=k?k.emptyScript:"";for(let i=0;i<t;i++)s.append(e[i],N()),W.nextNode(),r.push({type:2,index:++a});s.append(e[t],N())}}}else if(8===s.nodeType)if(s.data===S)r.push({type:2,index:a});else{let e=-1;for(;-1!==(e=s.data.indexOf(E,e+1));)r.push({type:7,index:a}),e+=E.length-1}a++}}static createElement(e,t){const i=P.createElement("template");return i.innerHTML=e,i}}function J(e,t,i=e,s){if(t===q)return t;let a=void 0!==s?i._$Co?.[s]:i._$Cl;const o=T(t)?void 0:t._$litDirective$;return a?.constructor!==o&&(a?._$AO?.(!1),void 0===o?a=void 0:(a=new o(e),a._$AT(e,i,s)),void 0!==s?(i._$Co??=[])[s]=a:i._$Cl=a),void 0!==a&&(t=J(e,a._$AS(e,t.values),a,s)),t}class G{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:i}=this._$AD,s=(e?.creationScope??P).importNode(t,!0);W.currentNode=s;let a=W.nextNode(),o=0,n=0,r=i[0];for(;void 0!==r;){if(o===r.index){let t;2===r.type?t=new Q(a,a.nextSibling,this,e):1===r.type?t=new r.ctor(a,r.name,r.strings,this,e):6===r.type&&(t=new ae(a,this,e)),this._$AV.push(t),r=i[++n]}o!==r?.index&&(a=W.nextNode(),o++)}return W.currentNode=P,s}p(e){let t=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(e,i,t),t+=i.strings.length-2):i._$AI(e[t])),t++}}class Q{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,i,s){this.type=2,this._$AH=B,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=i,this.options=s,this._$Cv=s?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return void 0!==t&&11===e?.nodeType&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=J(this,e,t),T(e)?e===B||null==e||""===e?(this._$AH!==B&&this._$AR(),this._$AH=B):e!==this._$AH&&e!==q&&this._(e):void 0!==e._$litType$?this.$(e):void 0!==e.nodeType?this.T(e):(e=>M(e)||"function"==typeof e?.[Symbol.iterator])(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==B&&T(this._$AH)?this._$AA.nextSibling.data=e:this.T(P.createTextNode(e)),this._$AH=e}$(e){const{values:t,_$litType$:i}=e,s="number"==typeof i?this._$AC(e):(void 0===i.el&&(i.el=Y.createElement(X(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===s)this._$AH.p(t);else{const e=new G(s,this),i=e.u(this.options);e.p(t),this.T(i),this._$AH=e}}_$AC(e){let t=Z.get(e.strings);return void 0===t&&Z.set(e.strings,t=new Y(e)),t}k(e){M(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let i,s=0;for(const a of e)s===t.length?t.push(i=new Q(this.O(N()),this.O(N()),this,this.options)):i=t[s],i._$AI(a),s++;s<t.length&&(this._$AR(i&&i._$AB.nextSibling,s),t.length=s)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){const t=C(e).nextSibling;C(e).remove(),e=t}}setConnected(e){void 0===this._$AM&&(this._$Cv=e,this._$AP?.(e))}}class ee{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,i,s,a){this.type=1,this._$AH=B,this._$AN=void 0,this.element=e,this.name=t,this._$AM=s,this.options=a,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=B}_$AI(e,t=this,i,s){const a=this.strings;let o=!1;if(void 0===a)e=J(this,e,t,0),o=!T(e)||e!==this._$AH&&e!==q,o&&(this._$AH=e);else{const s=e;let n,r;for(e=a[0],n=0;n<a.length-1;n++)r=J(this,s[i+n],t,n),r===q&&(r=this._$AH[n]),o||=!T(r)||r!==this._$AH[n],r===B?e=B:e!==B&&(e+=(r??"")+a[n+1]),this._$AH[n]=r}o&&!s&&this.j(e)}j(e){e===B?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class te extends ee{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===B?void 0:e}}class ie extends ee{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==B)}}class se extends ee{constructor(e,t,i,s,a){super(e,t,i,s,a),this.type=5}_$AI(e,t=this){if((e=J(this,e,t,0)??B)===q)return;const i=this._$AH,s=e===B&&i!==B||e.capture!==i.capture||e.once!==i.once||e.passive!==i.passive,a=e!==B&&(i===B||s);s&&this.element.removeEventListener(this.name,this,i),a&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}}class ae{constructor(e,t,i){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(e){J(this,e)}}const oe=w.litHtmlPolyfillSupport;oe?.(Y,Q),(w.litHtmlVersions??=[]).push("3.3.2");const ne=globalThis;class re extends x{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=((e,t,i)=>{const s=i?.renderBefore??t;let a=s._$litPart$;if(void 0===a){const e=i?.renderBefore??null;s._$litPart$=a=new Q(t.insertBefore(N(),e),e,void 0,i??{})}return a._$AI(e),a})(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return q}}re._$litElement$=!0,re.finalized=!0,ne.litElementHydrateSupport?.({LitElement:re});const de=ne.litElementPolyfillSupport;de?.({LitElement:re}),(ne.litElementVersions??=[]).push("4.2.2");const ce=e=>(t,i)=>{void 0!==i?i.addInitializer(()=>{customElements.define(e,t)}):customElements.define(e,t)},le={attribute:!0,type:String,converter:y,reflect:!1,hasChanged:f},he=(e=le,t,i)=>{const{kind:s,metadata:a}=i;let o=globalThis.litPropertyMetadata.get(a);if(void 0===o&&globalThis.litPropertyMetadata.set(a,o=new Map),"setter"===s&&((e=Object.create(e)).wrapped=!0),o.set(i.name,e),"accessor"===s){const{name:s}=i;return{set(i){const a=t.get.call(this);t.set.call(this,i),this.requestUpdate(s,a,e,!0,i)},init(t){return void 0!==t&&this.C(s,void 0,e,t),t}}}if("setter"===s){const{name:s}=i;return function(i){const a=this[s];t.call(this,i),this.requestUpdate(s,a,e,!0,i)}}throw Error("Unsupported decorator location: "+s)};function pe(e){return(t,i)=>"object"==typeof i?he(e,t,i):((e,t,i)=>{const s=t.hasOwnProperty(i);return t.constructor.createProperty(i,e),s?Object.getOwnPropertyDescriptor(t,i):void 0})(e,t,i)}function ue(e){return pe({...e,state:!0,attribute:!1})}class ve{constructor(e){this.hass=e}listDevices(){return this.hass.connection.sendMessagePromise({type:"hair/devices"})}getDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/device",device_id:e})}createDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/device/create",...e})}updateDevice(e,t){return this.hass.connection.sendMessagePromise({type:"hair/device/update",device_id:e,...t})}deleteDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/device/delete",device_id:e})}deleteCommand(e,t){return this.hass.connection.sendMessagePromise({type:"hair/command/delete",device_id:e,command_id:t})}sendCommand(e,t){return this.hass.connection.sendMessagePromise({type:"hair/command/send",device_id:e,command_id:t})}listTemplates(e){return this.hass.connection.sendMessagePromise({type:"hair/templates",device_type:e})}listCaptureProviders(){return this.hass.connection.sendMessagePromise({type:"hair/capture/providers"})}async startCapture(e,t,i){let s=null;const a=await this.hass.connection.subscribeMessage(e=>{e.type?.startsWith("capture_")?i(e):e.session_id&&(s=e)},{type:"hair/capture/start",device_id:e,timeout:t});if(await Promise.resolve(),null===s)throw new Error("Capture session did not start");return{session:s,unsubscribe:a}}cancelCapture(e){return this.hass.connection.sendMessagePromise({type:"hair/capture/cancel",session_id:e})}saveCapturedCommand(e){return this.hass.connection.sendMessagePromise({type:"hair/capture/save",...e})}getUnknownDevices(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/devices",...e})}getUnknownDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/device",device_id:e})}dismissUnknown(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/dismiss",device_id:e})}undismissUnknown(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/undismiss",device_id:e})}assignSignal(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/assign",...e})}assignToNewDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/assign-new-device",...e})}deleteSignal(e,t){return this.hass.connection.sendMessagePromise({type:"hair/unknown/signal/delete",device_id:e,signal_fingerprint:t})}testSignal(e,t){const i={type:"hair/unknown/test",signal_fingerprint:e};return t&&(i.emitter_entity_id=t),this.hass.connection.sendMessagePromise(i)}renameUnknown(e,t){return this.hass.connection.sendMessagePromise({type:"hair/unknown/rename",device_id:e,label:t})}clearUnknowns(){return this.hass.connection.sendMessagePromise({type:"hair/unknown/clear"})}async subscribeUnknownSignals(e){return this.hass.connection.subscribeEvents(t=>e(t.data),"hair_signal_detected")}async subscribeSignalRemoved(e){return this.hass.connection.subscribeEvents(t=>e(t.data),"hair_signal_removed")}}let me=class extends re{constructor(){super(...arguments),this.templateName="",this.command=null,this.busy=!1}_commandLabel(){const e=this.command;return e.protocol&&e.code?`${e.protocol}: ${e.code}`:e.raw_timings?.length?`RAW: ${e.raw_timings.length} timings`:e.protocol??"IR"}_prontoSlArray(e){const t=e.trim().split(/\s+/);if(t.length<6)return null;const i=parseInt(t[2],16)+parseInt(t[3],16),s=t.slice(4);if(s.length<2*i)return null;const a=[];for(let e=0;e<2*i;e++){const t=parseInt(s[e],16);a.push(t>=48)}return a.length>0?a:null}_renderDiamonds(){const e=this.command;if(!e||"PRONTO"!==e.protocol?.toUpperCase()||!e.code)return null;const t=this._prontoSlArray(e.code);return t?F`<span class="diamonds">${t.map(e=>e?F`<span class="diamond long">◆</span>`:F`<span class="diamond short">◇</span>`)}</span>`:null}_emit(e){this.dispatchEvent(new CustomEvent(e,{detail:{templateName:this.templateName,command:this.command},bubbles:!0,composed:!0}))}render(){const e=null!==this.command,t=e?this._renderDiamonds():null;return F`
            <div class="row" data-learned=${e?"true":"false"}>
                <div class="status" aria-hidden="true">
                    ${e?F`<span class="dot learned"></span>`:F`<span class="dot unlearned"></span>`}
                </div>
                <div class="info">
                    <div class="name">${this.templateName}</div>
                    <div class="meta">
                        ${t||(e?F`${this._commandLabel()}`:F`<span class="muted">Not yet learned</span>`)}
                    </div>
                </div>
                <div class="actions">
                    ${e?F`
                              <button
                                  class="action-btn test-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("test")}
                              >Test</button>
                              <button
                                  class="action-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("relearn")}
                              >Re-learn</button>
                              <button
                                  class="action-btn delete-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("delete")}
                              >Delete</button>
                          `:F`
                              <button
                                  class="action-btn learn-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("learn")}
                              >Learn</button>
                          `}
                </div>
            </div>
        `}};me.styles=n`
        :host {
            display: block;
        }
        .row {
            display: grid;
            grid-template-columns: 32px 1fr auto;
            align-items: center;
            gap: 12px;
            padding: 10px 12px;
            border-bottom: 1px solid var(--divider-color);
            box-shadow: 0 1px 0 rgba(0, 0, 0, 0.04);
        }
        .row:last-child {
            border-bottom: none;
            box-shadow: none;
        }
        .row[data-learned="false"] {
            background: var(--secondary-background-color);
        }
        .status {
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .dot {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }
        .dot.learned {
            background: #2e7d32;
        }
        .dot.unlearned {
            border: 2px solid var(--disabled-text-color, #999);
            width: 8px;
            height: 8px;
            background: transparent;
        }
        .name {
            font-weight: 500;
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
        .action-btn.delete-btn {
            color: #b71c1c;
            border-color: rgba(183, 28, 28, 0.2);
        }
        .action-btn.delete-btn:hover {
            background: rgba(183, 28, 28, 0.06);
        }
    `,e([pe({attribute:!1})],me.prototype,"templateName",void 0),e([pe({attribute:!1})],me.prototype,"command",void 0),e([pe({type:Boolean})],me.prototype,"busy",void 0),me=e([ce("ir-command-row")],me);let _e=class extends re{constructor(){super(...arguments),this.commandName="",this.timeout=15,this._phase="listening",this._result=null,this._duplicate=null,this._error=null,this._timeRemaining=0,this._sessionId=null,this._unsubscribe=null,this._countdown=null}connectedCallback(){super.connectedCallback(),this._beginCapture()}disconnectedCallback(){super.disconnectedCallback(),this._stopCountdown(),this._unsubscribe&&(this._unsubscribe(),this._unsubscribe=null)}async _beginCapture(){this._phase="listening",this._result=null,this._duplicate=null,this._error=null,this._timeRemaining=this.timeout,this._startCountdown();try{const{session:e,unsubscribe:t}=await this.api.startCapture(this.device.id,this.timeout,e=>this._onCaptureEvent(e));this._sessionId=e.session_id,this._unsubscribe=t}catch(e){this._stopCountdown(),this._error=e.message,this._phase="error"}}_onCaptureEvent(e){switch(e.type){case"capture_listening":this._phase="listening";break;case"capture_received":this._stopCountdown(),this._result=e.result,e.duplicate_of?(this._duplicate=e.duplicate_of,this._phase="duplicate"):this._phase="captured";break;case"capture_timeout":this._stopCountdown(),this._phase="timeout";break;case"capture_error":this._stopCountdown(),this._error=e.error,this._phase="error";break;case"capture_cancelled":this._stopCountdown(),this._close()}}_startCountdown(){this._stopCountdown();const e=Date.now();this._countdown=window.setInterval(()=>{const t=(Date.now()-e)/1e3;this._timeRemaining=Math.max(0,Math.ceil(this.timeout-t)),this._timeRemaining<=0&&this._stopCountdown()},250)}_stopCountdown(){null!==this._countdown&&(clearInterval(this._countdown),this._countdown=null)}async _cancel(){if(this._sessionId)try{await this.api.cancelCapture(this._sessionId)}catch{}this._close()}async _testCommand(){if(!this._sessionId)return;const e=`__hair_test_${Date.now()}`;try{const t=await this.api.saveCapturedCommand({device_id:this.device.id,session_id:this._sessionId,command_name:e});await this.api.sendCommand(this.device.id,t.id),await this.api.deleteCommand(this.device.id,t.id)}catch(e){this._error=e.message,this._phase="error"}}async _save(e){if(this._sessionId)try{await this.api.saveCapturedCommand({device_id:this.device.id,session_id:this._sessionId,command_name:this.commandName}),this.dispatchEvent(new CustomEvent("command-saved",{detail:{saveAndNext:e,commandName:this.commandName},bubbles:!0,composed:!0})),this._close()}catch(e){this._error=e.message,this._phase="error"}}async _recapture(){this._unsubscribe&&(await this._unsubscribe(),this._unsubscribe=null),await this._beginCapture()}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_renderListening(){return F`
            <div class="phase listening" aria-live="polite">
                <div class="pulse" aria-hidden="true">
                    <span></span><span></span><span></span>
                </div>
                <div class="title">Listening for IR signal…</div>
                <div class="instruction">
                    Point your remote at the IR receiver and press the
                    "${this.commandName}" button.
                </div>
                <div class="countdown">
                    ${this._timeRemaining}s remaining
                </div>
                <div class="actions">
                    <mwc-button @click=${this._cancel}>Cancel</mwc-button>
                </div>
            </div>
        `}_renderCaptured(){const e=this._result;return F`
            <div class="phase captured" aria-live="polite">
                <div class="check" aria-hidden="true">✓</div>
                <div class="title">Signal Captured!</div>
                <div class="meta">
                    Protocol: ${e.protocol??"Raw"}${e.code?F` · <code>${e.code}</code>`:""}
                </div>
                <ha-alert alert-type="info">
                    Did it work? Press Test to verify.
                </ha-alert>
                <div class="actions">
                    <mwc-button @click=${this._testCommand}>▶ Test</mwc-button>
                    <mwc-button @click=${this._recapture}>↻ Re-capture</mwc-button>
                    <mwc-button raised @click=${()=>this._save(!0)}>
                        Save &amp; Learn Next ▶▶
                    </mwc-button>
                </div>
            </div>
        `}_renderTimeout(){return F`
            <div class="phase error" aria-live="assertive">
                <div class="title warn">⚠ No signal detected</div>
                <ul class="tips">
                    <li>Point the remote directly at the IR receiver</li>
                    <li>Move closer (within 3 feet / 1 meter)</li>
                    <li>Press and hold the button briefly</li>
                </ul>
                <div class="actions">
                    <mwc-button raised @click=${this._recapture}>↻ Try Again</mwc-button>
                    <mwc-button @click=${this._cancel}>Cancel</mwc-button>
                </div>
            </div>
        `}_renderDuplicate(){const e=this._result;return F`
            <div class="phase warning" aria-live="assertive">
                <div class="title warn">⚠ Duplicate Signal Detected</div>
                <div class="instruction">
                    This matches your "${this._duplicate.name}" command.
                    Some remotes use the same signal for multiple buttons.
                </div>
                <div class="meta">
                    Protocol: ${e.protocol??"Raw"}
                </div>
                <div class="actions">
                    <mwc-button @click=${this._recapture}>
                        Re-capture Different
                    </mwc-button>
                    <mwc-button raised @click=${()=>this._save(!0)}>
                        Save Anyway
                    </mwc-button>
                </div>
            </div>
        `}_renderError(){return F`
            <div class="phase error" aria-live="assertive">
                <div class="title warn">⚠ Capture Error</div>
                <div class="instruction">${this._error}</div>
                <div class="actions">
                    <mwc-button raised @click=${this._recapture}>
                        ↻ Try Again
                    </mwc-button>
                    <mwc-button @click=${this._cancel}>Cancel</mwc-button>
                </div>
            </div>
        `}render(){return F`
            <ha-dialog
                open
                heading=${`Learning: "${this.commandName}"`}
                @closed=${this._cancel}
            >
                ${"listening"===this._phase?this._renderListening():"captured"===this._phase?this._renderCaptured():"timeout"===this._phase?this._renderTimeout():"duplicate"===this._phase?this._renderDuplicate():this._renderError()}
            </ha-dialog>
        `}};_e.styles=n`
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
    `,e([pe({attribute:!1})],_e.prototype,"api",void 0),e([pe({attribute:!1})],_e.prototype,"hass",void 0),e([pe({attribute:!1})],_e.prototype,"device",void 0),e([pe({attribute:!1})],_e.prototype,"commandName",void 0),e([pe({attribute:!1})],_e.prototype,"timeout",void 0),e([ue()],_e.prototype,"_phase",void 0),e([ue()],_e.prototype,"_result",void 0),e([ue()],_e.prototype,"_duplicate",void 0),e([ue()],_e.prototype,"_error",void 0),e([ue()],_e.prototype,"_timeRemaining",void 0),e([ue()],_e.prototype,"_sessionId",void 0),_e=e([ce("ir-capture-dialog")],_e);let ge=class extends re{constructor(){super(...arguments),this.title="Confirm",this.message="Are you sure?",this.confirmLabel="Confirm",this.cancelLabel="Cancel",this.destructive=!1,this._busy=!1}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_confirm(){this.dispatchEvent(new CustomEvent("confirmed",{bubbles:!0,composed:!0}))}render(){return F`
            <div class="overlay" @click=${this._close}>
                <div class="dialog" @click=${e=>e.stopPropagation()}>
                    <h3 class="heading">${this.title}</h3>
                    <p class="message">${this.message}</p>
                    <div class="actions">
                        <button class="btn cancel" @click=${this._close}>
                            ${this.cancelLabel}
                        </button>
                        <button
                            class="btn confirm ${this.destructive?"destructive":""}"
                            @click=${this._confirm}
                        >
                            ${this.confirmLabel}
                        </button>
                    </div>
                </div>
            </div>
        `}};ge.styles=n`
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
            margin: 0 0 12px;
            font-size: 1.1rem;
            font-weight: 500;
            color: var(--primary-text-color);
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
            background: var(--error-color, #db4437);
            border-color: var(--error-color, #db4437);
        }
    `,e([pe()],ge.prototype,"title",void 0),e([pe()],ge.prototype,"message",void 0),e([pe()],ge.prototype,"confirmLabel",void 0),e([pe()],ge.prototype,"cancelLabel",void 0),e([pe({type:Boolean})],ge.prototype,"destructive",void 0),e([ue()],ge.prototype,"_busy",void 0),ge=e([ce("ir-confirm-dialog")],ge);let be=class extends re{constructor(){super(...arguments),this.value=[],this.disabled=!1,this._didAutoSelect=!1}updated(e){if(super.updated(e),!this._didAutoSelect&&0===this.value.length){const e=this._getEmitters();1===e.length&&(this._didAutoSelect=!0,this._fireChange([e[0].entity_id]))}}_getEmitters(){const e=this.hass?.states??{},t=[];for(const[i,s]of Object.entries(e))i.startsWith("infrared.")&&t.push({entity_id:i,name:s.attributes.friendly_name??i});return t}_emitterName(e){const t=this.hass?.states?.[e];return t?.attributes?.friendly_name??e}_onAdd(e){const t=e.target,i=t.value;i&&(t.value="",this.value.includes(i)||this._fireChange([...this.value,i]))}_onRemove(e){this._fireChange(this.value.filter(t=>t!==e))}_fireChange(e){this.value=e,this.dispatchEvent(new CustomEvent("emitters-changed",{detail:{value:e},bubbles:!0,composed:!0}))}render(){const e=this._getEmitters(),t=e.filter(e=>!this.value.includes(e.entity_id));return F`
            <label>IR emitters</label>

            ${this.value.length>0?F`
                      <div class="chips">
                          ${this.value.map(e=>F`
                                  <span class="chip">
                                      <span class="chip-name">${this._emitterName(e)}</span>
                                      ${this.disabled?"":F`<button
                                                class="chip-remove"
                                                @click=${()=>this._onRemove(e)}
                                                title="Remove"
                                            >&times;</button>`}
                                  </span>
                              `)}
                      </div>
                  `:""}

            ${0===e.length?F`<div class="no-emitters">No IR emitters found.</div>`:t.length>0?F`
                        <select
                            @change=${this._onAdd}
                            ?disabled=${this.disabled}
                        >
                            <option value="">+ Add emitter...</option>
                            ${t.map(e=>F`
                                    <option value=${e.entity_id}>
                                        ${e.name}
                                    </option>
                                `)}
                        </select>
                    `:this.value.length>0?F`<div class="all-selected">All emitters selected.</div>`:""}
        `}};be.styles=n`
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
            background: rgba(46, 125, 50, 0.12);
            color: #2e7d32;
            font-size: 0.82rem;
            font-weight: 500;
            padding: 4px 8px;
            border-radius: 14px;
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
    `,e([pe({attribute:!1})],be.prototype,"hass",void 0),e([pe({attribute:!1})],be.prototype,"value",void 0),e([pe({type:Boolean})],be.prototype,"disabled",void 0),e([ue()],be.prototype,"_didAutoSelect",void 0),be=e([ce("ir-emitter-picker")],be);const ye=[{value:"tv",label:"TV / Monitor"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"soundbar",label:"Soundbar / Audio"},{value:"projector",label:"Projector"},{value:"other",label:"Other"}];let fe=class extends re{constructor(){super(...arguments),this._busy=!1,this._captureName=null,this._toast=null,this._confirmDelete=!1,this._commandToDelete=null,this._editingName=!1,this._draftName=""}_emitterName(e){const t=this.hass?.states?.[e];return t?.attributes?.friendly_name??e}_deviceRegistryName(e){const t=this.hass?.devices?.[e];return t?.name_by_user??t?.name??e}_deviceConfigEntryId(e){const t=this.hass?.devices?.[e];return t?(t.config_entries??[])[0]??null:null}_configEntryDomain(e){const t=this.hass?.config_entries?.entries?.[e];return t?.domain??null}_integrationUrl(e){if(!e)return null;const t=this._configEntryDomain(e);return t?`/config/integrations/integration/${t}`:null}_entityIntegrationUrl(e){const t=e.split(".")[0],i=this.hass?.entities?.[e];return i?.config_entry_id?this._integrationUrl(i.config_entry_id):i?.platform?`/config/integrations/integration/${i.platform}`:`/config/integrations/integration/${t}`}async _refresh(){this.device=await this.api.getDevice(this.device.id),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}_flash(e){this._toast=e,setTimeout(()=>{this._toast=null},2400)}_startEditName(){this._draftName=this.device.name,this._editingName=!0,this.updateComplete.then(()=>{const e=this.shadowRoot?.querySelector(".name-input");e?.focus(),e?.select()})}async _saveName(){const e=this._draftName.trim();if(e&&e!==this.device.name){this._busy=!0;try{this.device=await this.api.updateDevice(this.device.id,{name:e}),this._flash("Name updated"),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Update failed: ${e.message}`)}finally{this._busy=!1,this._editingName=!1}}else this._editingName=!1}_onNameKeyDown(e){"Enter"===e.key?(e.preventDefault(),this._saveName()):"Escape"===e.key&&(this._editingName=!1)}async _onTypeChanged(e){const t=e.target.value;if(t!==this.device.device_type){this._busy=!0;try{this.device=await this.api.updateDevice(this.device.id,{device_type:t}),this._flash("Device type updated"),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Update failed: ${e.message}`)}finally{this._busy=!1}}}async _onEmittersChanged(e){const t=e.detail.value;this._busy=!0;try{this.device=await this.api.updateDevice(this.device.id,{emitter_entity_ids:t}),this._flash("Emitters updated"),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Update failed: ${e.message}`)}finally{this._busy=!1}}async _onRelearn(e){const{templateName:t}=e.detail;this._captureName=t}async _onTest(e){const{command:t}=e.detail;if(t){this._busy=!0;try{await this.api.sendCommand(this.device.id,t.id),this._flash(`Sent "${t.name}"`)}catch(e){this._flash(`Send failed: ${e.message}`)}finally{this._busy=!1}}}_onDelete(e){const{command:t}=e.detail;t&&(this._commandToDelete=t)}async _confirmCommandDelete(){const e=this._commandToDelete;if(e){this._commandToDelete=null,this._busy=!0;try{await this.api.deleteCommand(this.device.id,e.id),await this._refresh(),this._flash(`Removed "${e.name}"`)}catch(e){this._flash(`Delete failed: ${e.message}`)}finally{this._busy=!1}}}_onCaptureClosed(){this._captureName=null}async _onCommandSaved(e){const{commandName:t}=e.detail;await this._refresh(),this._flash(`Saved "${t}"`),this._captureName=null}_goToSniffer(){this.dispatchEvent(new CustomEvent("navigate-sniffer",{bubbles:!0,composed:!0}))}async _deleteDevice(){this._busy=!0;try{await this.api.deleteDevice(this.device.id),this.dispatchEvent(new CustomEvent("device-deleted",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Delete failed: ${e.message}`)}finally{this._busy=!1,this._confirmDelete=!1}}_navigateIntegration(e){e&&(window.history.pushState(null,"",e),window.dispatchEvent(new PopStateEvent("popstate")))}render(){const e=this.device.commands,t=e.length;return F`
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
                                  title="Click to rename"
                              >
                                  ${this.device.name}
                                  <span class="edit-icon">&#9998;</span>
                              </h1>
                          `}
                </div>
                <div class="header-actions">
                    <button
                        class="action-btn collapse-btn"
                        @click=${()=>this.dispatchEvent(new CustomEvent("collapse",{bubbles:!0,composed:!0}))}
                        title="Close"
                    >&#x2715;</button>
                    <button
                        class="action-btn delete-btn"
                        @click=${()=>this._confirmDelete=!0}
                        ?disabled=${this._busy}
                    >Delete</button>
                </div>
            </section>

            <!-- Device metadata grid -->
            <div class="device-meta">
                <span class="meta-label">Type</span>
                <div class="meta-value">
                    <select
                        .value=${this.device.device_type}
                        @change=${this._onTypeChanged}
                        ?disabled=${this._busy}
                    >
                        ${ye.map(e=>F`
                                <option
                                    value=${e.value}
                                    ?selected=${this.device.device_type===e.value}
                                >
                                    ${e.label}
                                </option>
                            `)}
                    </select>
                </div>
                <span class="meta-label">Emitters</span>
                <div class="meta-value">
                    <ir-emitter-picker
                        .hass=${this.hass}
                        .value=${this.device.emitter_entity_ids??[]}
                        ?disabled=${this._busy}
                        @emitters-changed=${this._onEmittersChanged}
                    ></ir-emitter-picker>
                </div>
            </div>

            <!-- Commands -->
            <ha-card>
                <h2>Commands (${t})</h2>
                ${e.length>0?e.map(e=>F`
                              <ir-command-row
                                  .templateName=${e.name}
                                  .command=${e}
                                  .busy=${this._busy}
                                  @relearn=${this._onRelearn}
                                  @test=${this._onTest}
                                  @delete=${this._onDelete}
                              ></ir-command-row>
                          `):F`<div class="empty">No commands yet. Add one below.</div>`}
            </ha-card>

            <div class="custom-add">
                <button
                    class="action-btn"
                    @click=${this._goToSniffer}
                    ?disabled=${this._busy}
                >+ Add Command</button>
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
                          title="Delete ${this.device.name}?"
                          message="This removes all captured commands and the auto-created entity. The action cannot be undone."
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._deleteDevice}
                          @closed=${()=>this._confirmDelete=!1}
                      ></ir-confirm-dialog>
                  `:""}
            ${this._commandToDelete?F`
                      <ir-confirm-dialog
                          title="Delete command?"
                          message="Remove &quot;${this._commandToDelete.name}&quot;? This cannot be undone."
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._confirmCommandDelete}
                          @closed=${()=>this._commandToDelete=null}
                      ></ir-confirm-dialog>
                  `:""}
            ${this._toast?F`<div class="toast" role="status">${this._toast}</div>`:""}
        `}};fe.styles=n`
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
        .header-actions {
            display: flex;
            gap: 6px;
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
        .action-btn.delete-btn {
            color: #b71c1c;
            border-color: rgba(183, 28, 28, 0.2);
        }
        .action-btn.delete-btn:hover {
            background: rgba(183, 28, 28, 0.06);
        }
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

        /* --- Commands card --- */
        ha-card {
            margin: 16px 0;
            padding: 16px;
        }
        ha-card h2 {
            margin: 0 0 8px;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.04em;
            color: var(--secondary-text-color);
        }
        .empty {
            color: var(--secondary-text-color);
            font-style: italic;
            padding: 12px 0;
        }
        .custom-add {
            margin: 16px 0;
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
    `,e([pe({attribute:!1})],fe.prototype,"api",void 0),e([pe({attribute:!1})],fe.prototype,"hass",void 0),e([pe({attribute:!1})],fe.prototype,"device",void 0),e([ue()],fe.prototype,"_busy",void 0),e([ue()],fe.prototype,"_captureName",void 0),e([ue()],fe.prototype,"_toast",void 0),e([ue()],fe.prototype,"_confirmDelete",void 0),e([ue()],fe.prototype,"_commandToDelete",void 0),e([ue()],fe.prototype,"_editingName",void 0),e([ue()],fe.prototype,"_draftName",void 0),fe=e([ce("ir-device-detail")],fe);const $e={tv:"M21,17H3V5H21M21,3H3A2,2 0 0,0 1,5V17A2,2 0 0,0 3,19H8V21H16V19H21A2,2 0 0,0 23,17V5A2,2 0 0,0 21,3Z",ac:"M11,21H13V11.85L14.6,13.5L16,12.05L12,8L8,12.05L9.4,13.5L11,11.85V21M2,3V11C2,12.66 5.69,14 12,14C18.31,14 22,12.66 22,11V3H2M4,5H20V8.5C18.5,9.27 15.6,10 12,10C8.4,10 5.5,9.27 4,8.5V5Z",fan:"M12,11A1,1 0 0,0 11,12A1,1 0 0,0 12,13A1,1 0 0,0 13,12A1,1 0 0,0 12,11M12.5,2C17,2 17.11,5.57 14.75,6.75C13.76,7.24 13.32,8.29 13.13,9.22C13.61,9.42 14.03,9.73 14.35,10.13C18.05,8.13 22.03,8.92 22.03,12.5C22.03,17 18.46,17.1 17.28,14.73C16.78,13.74 15.72,13.3 14.79,13.11C14.59,13.59 14.28,14 13.88,14.34C15.87,18.03 15.08,22 11.5,22C7,22 6.91,18.42 9.27,17.24C10.25,16.75 10.69,15.71 10.89,14.79C10.4,14.59 9.97,14.27 9.65,13.87C5.96,15.85 2,15.07 2,11.5C2,7 5.56,6.89 6.74,9.26C7.24,10.25 8.29,10.68 9.22,10.87C9.41,10.39 9.73,9.97 10.14,9.65C8.15,5.95 8.94,2 12.5,2Z",soundbar:"M16,4V8H8V4H16M3,9V14H21V9H3M2,16C2,17.1 2.9,18 4,18H20C21.1,18 22,17.1 22,16V8C22,6.89 21.1,6 20,6H4C2.89,6 2,6.89 2,8V16Z",projector:"M4,5A2,2 0 0,0 2,7V17A2,2 0 0,0 4,19H10V21H14V19H20A2,2 0 0,0 22,17V7A2,2 0 0,0 20,5H4M14,8A4,4 0 0,1 18,12A4,4 0 0,1 14,16A4,4 0 0,1 10,12A4,4 0 0,1 14,8M5,9A1,1 0 0,1 6,10A1,1 0 0,1 5,11A1,1 0 0,1 4,10A1,1 0 0,1 5,9M14,10A2,2 0 0,0 12,12A2,2 0 0,0 14,14A2,2 0 0,0 16,12A2,2 0 0,0 14,10Z",other:"M11,2A2,2 0 0,0 9,4V8H4A2,2 0 0,0 2,10V13A2,2 0 0,0 4,15H5V21A2,2 0 0,0 7,23H17A2,2 0 0,0 19,21V15H20A2,2 0 0,0 22,13V10A2,2 0 0,0 20,8H15V4A2,2 0 0,0 13,2H11Z"},xe={tv:"TV",ac:"Air Conditioner",fan:"Fan",soundbar:"Soundbar",projector:"Projector",other:"IR Device"};let we=class extends re{constructor(){super(...arguments),this.devices=[],this.loading=!1,this.expandedDeviceId=null,this._emitters=[],this._captureProviders=[],this._expandedDevice=null}connectedCallback(){super.connectedCallback(),this._discoverHardware()}updated(e){(e.has("hass")||e.has("api"))&&this._discoverHardware(),e.has("expandedDeviceId")&&this._loadExpandedDevice()}async _loadExpandedDevice(){if(this.expandedDeviceId&&this.api)try{this._expandedDevice=await this.api.getDevice(this.expandedDeviceId)}catch{this._expandedDevice=null}else this._expandedDevice=null}async _onExpandedDeviceChanged(){await this._loadExpandedDevice(),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}_onExpandedDeviceDeleted(){this.dispatchEvent(new CustomEvent("device-deleted",{bubbles:!0,composed:!0}))}_onCollapse(){this.dispatchEvent(new CustomEvent("device-selected",{detail:this.expandedDeviceId,bubbles:!0,composed:!0}))}async _discoverHardware(){const e=this.hass?.states??{},t=[];for(const[i,s]of Object.entries(e))i.startsWith("infrared.")&&t.push({entity_id:i,name:s.attributes.friendly_name??i});if(this._emitters=t,this.api)try{this._captureProviders=await this.api.listCaptureProviders()}catch{}}_select(e){this.dispatchEvent(new CustomEvent("device-selected",{detail:e,bubbles:!0,composed:!0}))}_add(){this.dispatchEvent(new CustomEvent("add-device",{bubbles:!0,composed:!0}))}_navigateIntegration(e){const t=`/config/integrations/integration/${e}`;window.history.pushState(null,"",t),window.dispatchEvent(new PopStateEvent("popstate"))}_emitterIntegrationDomain(e){const t=this.hass?.entities?.[e];return t?.platform?t.platform:e.split(".")[0]}_getEmitterDeviceIds(){const e=new Set;for(const t of this._emitters){const i=this.hass?.entities?.[t.entity_id];i?.device_id&&e.add(i.device_id)}return e}_classifyHardware(){const e=this._getEmitterDeviceIds();return{receivers:this._captureProviders,proxies:this._captureProviders.filter(t=>e.has(t.device_id))}}render(){if(this.loading)return F`<div class="loading">Loading IR devices...</div>`;const e=this.devices.length>0,t=this._emitters.length>0,{receivers:i,proxies:s}=this._classifyHardware(),a=i.length>0,o=s.length>0;return e||t||a||o?F`
            <!-- Devices -->
            ${e?F`
                      <div class="section-header">
                          <h2>Devices</h2>
                          <span class="section-count">${this.devices.length}</span>
                      </div>
                      <div class="grid">
                          ${this.devices.map(e=>F`
                                  <div
                                      class="card device-card ${e.id===this.expandedDeviceId?"expanded":""}"
                                      tabindex="0"
                                      @click=${()=>this._select(e.id)}
                                      @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._select(e.id))}}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon
                                              .path=${$e[e.device_type]??$e.other}
                                          ></ha-svg-icon>
                                          <div class="card-name">
                                              ${e.name}
                                          </div>
                                      </div>
                                      <div class="card-meta">
                                          ${[e.manufacturer,xe[e.device_type]].filter(Boolean).join(" • ")}
                                      </div>
                                      <div class="card-footer">
                                          <span class="badge cmd-badge">
                                              ${e.command_count} commands
                                          </span>
                                          ${e.emitter_entity_ids.length>0?F`<span class="badge tx-badge">TX: ${e.emitter_entity_ids.length}</span>`:F`<span class="badge no-tx-badge">No TX</span>`}
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
                                                    @collapse=${this._onCollapse}
                                                ></ir-device-detail>
                                            </div>
                                        `:B}
                              `)}
                      </div>
                  `:B}

            <!-- Emitters -->
            ${t?F`
                      <div class="section-header">
                          <h2>Emitters</h2>
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
                                          <ha-svg-icon .path=${"M12,10A2,2 0 0,1 14,12C14,12.5 13.82,12.95 13.53,13.29L16.7,16.46C17.5,15.26 18,13.71 18,12A6,6 0 0,0 12,6A6,6 0 0,0 6,12C6,13.71 6.5,15.26 7.3,16.46L10.47,13.29C10.18,12.95 10,12.5 10,12A2,2 0 0,1 12,10M12,2A10,10 0 0,0 2,12C2,15.07 3.18,17.85 5.09,19.91L7.5,17.5C6.19,15.89 5.5,14 5.5,12A6.5,6.5 0 0,1 12,5.5A6.5,6.5 0 0,1 18.5,12C18.5,14 17.81,15.89 16.5,17.5L18.91,19.91C20.82,17.85 22,15.07 22,12A10,10 0 0,0 12,2Z"}></ha-svg-icon>
                                          <div class="card-name">${e.name}</div>
                                      </div>
                                      <div class="card-meta">${e.entity_id}</div>
                                      <div class="card-footer">
                                          <span class="badge tx-badge">TX</span>
                                      </div>
                                  </div>
                              `)}
                      </div>
                  `:B}

            <!-- Receivers (RX-only hardware) -->
            ${a?F`
                      <div class="section-header">
                          <h2>Receivers</h2>
                          <span class="section-count">${i.length}</span>
                      </div>
                      <div class="grid">
                          ${i.map(e=>F`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      @click=${()=>this._navigateIntegration(e.type)}
                                      @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._navigateIntegration(e.type))}}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon .path=${"M12,6C8.69,6 6,8.69 6,12L4,12C4,7.58 7.58,4 12,4C16.42,4 20,7.58 20,12H18C18,8.69 15.31,6 12,6M12,10C10.9,10 10,10.9 10,12H8A4,4 0 0,1 12,8A4,4 0 0,1 16,12H14C14,10.9 13.1,10 12,10M13,14.05V19.5C13,20.33 12.33,21 11.5,21C10.67,21 10,20.33 10,19.5V14.05C9.38,13.67 9,13 9,12.25C9,11 10,10 11.25,10C12.5,10 13.5,11 13.5,12.25C13.5,13 13.12,13.67 12.5,14.05H13Z"}></ha-svg-icon>
                                          <div class="card-name">${e.name}</div>
                                      </div>
                                      <div class="card-meta">${e.type}</div>
                                      <div class="card-footer">
                                          <span class="badge rx-badge">RX</span>
                                      </div>
                                  </div>
                              `)}
                      </div>
                  `:B}

            <!-- Proxies (TX + RX hardware) -->
            ${o?F`
                      <div class="section-header">
                          <h2>Proxies</h2>
                          <span class="section-count">${s.length}</span>
                      </div>
                      <div class="grid">
                          ${s.map(e=>F`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      @click=${()=>this._navigateIntegration(e.type)}
                                      @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._navigateIntegration(e.type))}}
                                  >
                                      <div class="card-header">
                                          <ha-svg-icon .path=${"M20,13A8,8 0 0,0 12,5A8,8 0 0,0 4,13H2A10,10 0 0,1 12,3A10,10 0 0,1 22,13H20M16,13A4,4 0 0,0 12,9A4,4 0 0,0 8,13H6A6,6 0 0,1 12,7A6,6 0 0,1 18,13H16M13,18H11V14H13V18M13,21H11V19H13V21Z"}></ha-svg-icon>
                                          <div class="card-name">${e.name}</div>
                                      </div>
                                      <div class="card-meta">${e.type}</div>
                                      <div class="card-footer">
                                          <span class="badge tx-badge">TX</span>
                                          <span class="badge rx-badge">RX</span>
                                      </div>
                                  </div>
                              `)}
                      </div>
                  `:B}
        `:F`
                <ha-card class="empty">
                    <h2>No IR devices yet</h2>
                    <p>Add your first device to get started.</p>
                    <mwc-button raised @click=${this._add}>+ Add Device</mwc-button>
                </ha-card>
            `}};we.styles=n`
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
            border-radius: 999px;
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
            transform: translateY(-1px);
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
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
            border-radius: 999px;
            padding: 2px 10px;
            font-size: 0.72rem;
            font-weight: 500;
        }

        /* Command count badge (green) */
        .cmd-badge {
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
        }

        /* TX badge (blue) */
        .tx-badge {
            background: rgba(30, 136, 229, 0.15);
            color: #1565c0;
        }

        /* RX badge (amber) */
        .rx-badge {
            background: rgba(255, 152, 0, 0.15);
            color: #e65100;
        }

        /* No TX warning (muted) */
        .no-tx-badge {
            background: var(--secondary-background-color);
            color: var(--disabled-text-color, #999);
            font-style: italic;
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
        .device-card.expanded {
            border-color: #2e7d32;
            box-shadow: 0 0 0 1px #2e7d32;
        }

        /* --- Hardware cards inherit shared .card styles --- */
        .hw-card {
            /* Neutral -- no per-section color backgrounds */
        }
    `,e([pe({attribute:!1})],we.prototype,"devices",void 0),e([pe({attribute:!1})],we.prototype,"hass",void 0),e([pe({attribute:!1})],we.prototype,"api",void 0),e([pe({type:Boolean})],we.prototype,"loading",void 0),e([pe({attribute:!1})],we.prototype,"expandedDeviceId",void 0),e([ue()],we.prototype,"_emitters",void 0),e([ue()],we.prototype,"_captureProviders",void 0),e([ue()],we.prototype,"_expandedDevice",void 0),we=e([ce("ir-device-list")],we);const Ce=[{value:"tv",label:"TV / Monitor"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"soundbar",label:"Soundbar / Audio"},{value:"projector",label:"Projector"},{value:"other",label:"Other"}];let ke=class extends re{constructor(){super(...arguments),this._name="",this._manufacturer="",this._model="",this._deviceType="tv",this._emitterIds=[],this._captureProviderId=null,this._captureProviders=[],this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this._loadCaptureProviders()}async _loadCaptureProviders(){try{this._captureProviders=await this.api.listCaptureProviders(),1===this._captureProviders.length&&(this._captureProviderId=this._captureProviders[0].device_id)}catch(e){this._error=`Could not load capture providers: ${e.message}`}}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _create(){if(this._name.trim())if(0!==this._emitterIds.length){this._busy=!0,this._error=null;try{const e=this._captureProviders.find(e=>e.device_id===this._captureProviderId),t=await this.api.createDevice({name:this._name.trim(),device_type:this._deviceType,emitter_entity_ids:this._emitterIds,manufacturer:this._manufacturer.trim()||null,model:this._model.trim()||null,capture_device_id:this._captureProviderId,capture_provider_type:e?.type??"esphome"});this.dispatchEvent(new CustomEvent("device-created",{detail:t,bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error="Pick at least one IR emitter.";else this._error="Name is required."}render(){return F`
            <ha-dialog
                open
                heading="Add IR Device"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?F`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <div class="field">
                    <label>Device type</label>
                    <select
                        .value=${this._deviceType}
                        @change=${e=>this._deviceType=e.target.value}
                    >
                        ${Ce.map(e=>F`
                                <option
                                    value=${e.value}
                                    ?selected=${this._deviceType===e.value}
                                >
                                    ${e.label}
                                </option>
                            `)}
                    </select>
                </div>

                <ha-textfield
                    label="Name"
                    .value=${this._name}
                    required
                    @input=${e=>this._name=e.target.value}
                ></ha-textfield>

                <ha-textfield
                    label="Brand (optional)"
                    .value=${this._manufacturer}
                    @input=${e=>this._manufacturer=e.target.value}
                ></ha-textfield>

                <ha-textfield
                    label="Model (optional)"
                    .value=${this._model}
                    @input=${e=>this._model=e.target.value}
                ></ha-textfield>

                <ir-emitter-picker
                    .hass=${this.hass}
                    .value=${this._emitterIds}
                    ?disabled=${this._busy}
                    @emitters-changed=${e=>this._emitterIds=e.detail.value}
                ></ir-emitter-picker>

                <div class="field">
                    <label>IR receiver (learns commands)</label>
                    ${0===this._captureProviders.length?F`<ha-alert alert-type="info">
                              No capture-capable devices detected. You can
                              still create the device and add commands by
                              importing them later.
                          </ha-alert>`:F`
                              <select
                                  .value=${this._captureProviderId??""}
                                  @change=${e=>this._captureProviderId=e.target.value||null}
                              >
                                  <option value="">None (no learning)</option>
                                  ${this._captureProviders.map(e=>F`
                                          <option
                                              value=${e.device_id}
                                              ?selected=${this._captureProviderId===e.device_id}
                                          >
                                              ${e.name} (${e.type})
                                          </option>
                                      `)}
                              </select>
                          `}
                </div>

                <mwc-button
                    slot="secondaryAction"
                    @click=${this._close}
                    ?disabled=${this._busy}
                >
                    Cancel
                </mwc-button>
                <mwc-button
                    slot="primaryAction"
                    raised
                    @click=${this._create}
                    ?disabled=${this._busy}
                >
                    Create
                </mwc-button>
            </ha-dialog>
        `}};ke.styles=n`
        ha-textfield,
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
        select {
            width: 100%;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
        }
        ha-alert {
            display: block;
            margin: 8px 0;
        }
    `,e([pe({attribute:!1})],ke.prototype,"api",void 0),e([pe({attribute:!1})],ke.prototype,"hass",void 0),e([ue()],ke.prototype,"_name",void 0),e([ue()],ke.prototype,"_manufacturer",void 0),e([ue()],ke.prototype,"_model",void 0),e([ue()],ke.prototype,"_deviceType",void 0),e([ue()],ke.prototype,"_emitterIds",void 0),e([ue()],ke.prototype,"_captureProviderId",void 0),e([ue()],ke.prototype,"_captureProviders",void 0),e([ue()],ke.prototype,"_busy",void 0),e([ue()],ke.prototype,"_error",void 0),ke=e([ce("ir-add-device-dialog")],ke);const De=[{value:"tv",label:"TV / Monitor"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"soundbar",label:"Soundbar / Audio"},{value:"projector",label:"Projector"},{value:"other",label:"Other"}];let Ae=class extends re{constructor(){super(...arguments),this.suggestedDeviceName="",this.initialMode="existing",this._mode="existing",this._devices=[],this._selectedDeviceId="",this._commandName="",this._newName="",this._newType="tv",this._newEmitterIds=[],this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this._mode=this.initialMode,this.suggestedDeviceName&&!this._newName&&(this._newName=this.suggestedDeviceName),this._loadDevices()}async _loadDevices(){try{if(this._devices=await this.api.listDevices(),this.suggestedDeviceName&&!this._selectedDeviceId){const e=this.suggestedDeviceName.toLowerCase(),t=this._devices.find(t=>t.name.toLowerCase()===e);t&&(this._selectedDeviceId=t.id)}}catch{}}_onDeviceSelected(e){this._selectedDeviceId=e.target.value}_onNewTypeChanged(e){this._newType=e.target.value}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _assign(){const e=this._commandName.trim();if(e){this._busy=!0,this._error=null;try{let t;if("existing"===this._mode){if(!this._selectedDeviceId)return this._error="Select a target device.",void(this._busy=!1);t=await this.api.assignSignal({device_id:this.unknownDeviceId,signal_fingerprint:this.signal.fingerprint,hair_device_id:this._selectedDeviceId,command_name:e})}else{if(!this._newName.trim())return this._error="Device name is required.",void(this._busy=!1);if(0===this._newEmitterIds.length)return this._error="Select at least one IR emitter.",void(this._busy=!1);t=await this.api.assignToNewDevice({device_id:this.unknownDeviceId,signal_fingerprint:this.signal.fingerprint,device_name:this._newName.trim(),device_type:this._newType,emitter_entity_ids:this._newEmitterIds,command_name:e})}t.assigned?this.dispatchEvent(new CustomEvent("signal-assigned",{detail:t,bubbles:!0,composed:!0})):this._error="Assignment failed. The signal may have a duplicate code on the target device."}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error="Command name is required."}_fmtTime(e){try{return new Date(e).toLocaleString(void 0,{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return e}}render(){const e=this.signal.protocol??"RAW",t=this.signal.frequency?`${Math.round(this.signal.frequency/1e3)}kHz`:"";return F`
            <ha-dialog
                open
                heading="Assign Signal"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?F`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <div class="signal-header">
                    ${this.suggestedDeviceName?F`<div class="device-name">${this.suggestedDeviceName}</div>`:""}
                    <div class="signal-detail">
                        ${this.signal.sl_pattern?F`<span class="diamonds">${[...this.signal.sl_pattern].map(e=>"L"===e?F`<span class="diamond long">&#9670;</span>`:F`<span class="diamond short">&#9671;</span>`)}</span>`:F`<span class="proto-label">${e}</span>`}
                    </div>
                    <div class="signal-stats">
                        <span>${this.signal.hit_count} hits</span>
                        ${t?F`<span>${t}</span>`:""}
                        <span>${this._fmtTime(this.signal.last_seen)}</span>
                    </div>
                </div>

                <!-- Mode tabs -->
                <div class="mode-tabs">
                    <button
                        class="mode-tab ${"existing"===this._mode?"active":""}"
                        @click=${()=>{this._mode="existing"}}
                    >
                        Existing Device
                    </button>
                    <button
                        class="mode-tab ${"new"===this._mode?"active":""}"
                        @click=${()=>{this._mode="new"}}
                    >
                        New Device
                    </button>
                </div>

                ${"existing"===this._mode?this._renderExistingMode():this._renderNewMode()}

                <!-- Command name (shared by both modes) -->
                ${this._renderCommandPicker()}

                <div class="dialog-actions">
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        Cancel
                    </button>
                    <button
                        class="action-btn assign-btn"
                        @click=${this._assign}
                        ?disabled=${this._busy}
                    >
                        ${this._busy?"Assigning...":"new"===this._mode?"Create & Assign":"Assign"}
                    </button>
                </div>
            </ha-dialog>
        `}_renderExistingMode(){return F`
            <div class="field">
                <label>Target device</label>
                ${0===this._devices.length?F`<ha-alert alert-type="info">
                          No devices yet. Switch to "New Device" to create one.
                      </ha-alert>`:F`
                          <select
                              .value=${this._selectedDeviceId}
                              @change=${this._onDeviceSelected}
                          >
                              <option value="" disabled>Select device...</option>
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
            <ha-textfield
                label="Device name"
                .value=${this._newName}
                required
                @input=${e=>this._newName=e.target.value}
            ></ha-textfield>

            <div class="field">
                <label>Device type</label>
                <select
                    .value=${this._newType}
                    @change=${this._onNewTypeChanged}
                >
                    ${De.map(e=>F`
                            <option
                                value=${e.value}
                                ?selected=${this._newType===e.value}
                            >
                                ${e.label}
                            </option>
                        `)}
                </select>
            </div>

            <ir-emitter-picker
                .hass=${this.hass}
                .value=${this._newEmitterIds}
                ?disabled=${this._busy}
                @emitters-changed=${e=>this._newEmitterIds=e.detail.value}
            ></ir-emitter-picker>
        `}_renderCommandPicker(){return F`
            <ha-textfield
                label="Command name"
                .value=${this._commandName}
                required
                @input=${e=>this._commandName=e.target.value}
            ></ha-textfield>
        `}};Ae.styles=n`
        ha-textfield,
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
        select {
            width: 100%;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
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

        .dialog-actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            margin-top: 20px;
            padding-top: 16px;
            border-top: 1px solid var(--divider-color);
        }
        .action-btn {
            padding: 8px 20px;
            border-radius: 4px;
            font-size: 0.9rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            border: none;
            transition: background 150ms ease, opacity 150ms ease;
        }
        .action-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .cancel-btn {
            background: transparent;
            color: var(--secondary-text-color);
        }
        .cancel-btn:hover:not(:disabled) {
            background: var(--secondary-background-color);
        }
        .assign-btn {
            background: var(--primary-color);
            color: var(--text-primary-color, #fff);
        }
        .assign-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `,e([pe({attribute:!1})],Ae.prototype,"api",void 0),e([pe({attribute:!1})],Ae.prototype,"hass",void 0),e([pe()],Ae.prototype,"unknownDeviceId",void 0),e([pe({attribute:!1})],Ae.prototype,"signal",void 0),e([pe()],Ae.prototype,"suggestedDeviceName",void 0),e([pe()],Ae.prototype,"initialMode",void 0),e([ue()],Ae.prototype,"_mode",void 0),e([ue()],Ae.prototype,"_devices",void 0),e([ue()],Ae.prototype,"_selectedDeviceId",void 0),e([ue()],Ae.prototype,"_commandName",void 0),e([ue()],Ae.prototype,"_newName",void 0),e([ue()],Ae.prototype,"_newType",void 0),e([ue()],Ae.prototype,"_newEmitterIds",void 0),e([ue()],Ae.prototype,"_busy",void 0),e([ue()],Ae.prototype,"_error",void 0),Ae=e([ce("ir-assign-signal-dialog")],Ae);const Ee=[{value:"tv",label:"TV / Monitor"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"soundbar",label:"Soundbar / Audio"},{value:"projector",label:"Projector"},{value:"other",label:"Other"}];let Se=class extends re{constructor(){super(...arguments),this.suggestedName="",this._name="",this._type="other",this._emitterIds=[],this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this.suggestedName&&!this._name&&(this._name=this.suggestedName)}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _create(){const e=this._name.trim();if(e)if(0!==this._emitterIds.length){this._busy=!0,this._error=null;try{await this.api.createDevice({name:e,device_type:this._type,emitter_entity_ids:this._emitterIds}),this.dispatchEvent(new CustomEvent("device-created",{bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error="Select at least one IR emitter.";else this._error="Device name is required."}render(){return F`
            <ha-dialog
                open
                heading="Promote to Device"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?F`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <p class="description">
                    Create a new HAIR device. You can then assign captured
                    signals to it as commands.
                </p>

                <ha-textfield
                    label="Device name"
                    .value=${this._name}
                    required
                    @input=${e=>this._name=e.target.value}
                ></ha-textfield>

                <div class="field">
                    <label>Device type</label>
                    <select
                        .value=${this._type}
                        @change=${e=>this._type=e.target.value}
                    >
                        ${Ee.map(e=>F`
                                <option
                                    value=${e.value}
                                    ?selected=${this._type===e.value}
                                >
                                    ${e.label}
                                </option>
                            `)}
                    </select>
                </div>

                <ir-emitter-picker
                    .hass=${this.hass}
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
                        Cancel
                    </button>
                    <button
                        class="action-btn create-btn"
                        @click=${this._create}
                        ?disabled=${this._busy}
                    >
                        ${this._busy?"Creating...":"Create Device"}
                    </button>
                </div>
            </ha-dialog>
        `}};function Ie(e){try{return new Date(e).toLocaleString(void 0,{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return e}}function Pe(e){try{const t=Date.now()-new Date(e).getTime();return t<6e4?"just now":t<36e5?`${Math.floor(t/6e4)} min ago`:t<864e5?`${Math.floor(t/36e5)}h ago`:`${Math.floor(t/864e5)}d ago`}catch{return""}}Se.styles=n`
        ha-textfield,
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
        select {
            width: 100%;
            padding: 8px;
            border-radius: 4px;
            border: 1px solid var(--divider-color);
            background: var(--card-background-color);
            color: var(--primary-text-color);
        }
        ha-alert {
            display: block;
            margin: 8px 0;
        }
        .description {
            font-size: 0.85rem;
            color: var(--secondary-text-color);
            margin: 0 0 8px;
        }
        .dialog-actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            margin-top: 20px;
            padding-top: 16px;
            border-top: 1px solid var(--divider-color);
        }
        .action-btn {
            padding: 8px 20px;
            border-radius: 4px;
            font-size: 0.9rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            border: none;
            transition: background 150ms ease, opacity 150ms ease;
        }
        .action-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .cancel-btn {
            background: transparent;
            color: var(--secondary-text-color);
        }
        .cancel-btn:hover:not(:disabled) {
            background: var(--secondary-background-color);
        }
        .create-btn {
            background: #2e7d32;
            color: #fff;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `,e([pe({attribute:!1})],Se.prototype,"api",void 0),e([pe({attribute:!1})],Se.prototype,"hass",void 0),e([pe()],Se.prototype,"suggestedName",void 0),e([ue()],Se.prototype,"_name",void 0),e([ue()],Se.prototype,"_type",void 0),e([ue()],Se.prototype,"_emitterIds",void 0),e([ue()],Se.prototype,"_busy",void 0),e([ue()],Se.prototype,"_error",void 0),Se=e([ce("ir-promote-dialog")],Se);const Ne="M4.93,4.93C3.12,6.74 2,9.24 2,12C2,14.76 3.12,17.26 4.93,19.07L6.34,17.66C4.89,16.22 4,14.22 4,12C4,9.79 4.89,7.78 6.34,6.34L4.93,4.93M19.07,4.93L17.66,6.34C19.11,7.78 20,9.79 20,12C20,14.22 19.11,16.22 17.66,17.66L19.07,19.07C20.88,17.26 22,14.76 22,12C22,9.24 20.88,6.74 19.07,4.93M7.76,7.76C6.67,8.85 6,10.35 6,12C6,13.65 6.67,15.15 7.76,16.24L9.17,14.83C8.45,14.11 8,13.11 8,12C8,10.89 8.45,9.89 9.17,9.17L7.76,7.76M16.24,7.76L14.83,9.17C15.55,9.89 16,10.89 16,12C16,13.11 15.55,14.11 14.83,14.83L16.24,16.24C17.33,15.15 18,13.65 18,12C18,10.35 17.33,8.85 16.24,7.76M12,10A2,2 0 0,0 10,12A2,2 0 0,0 12,14A2,2 0 0,0 14,12A2,2 0 0,0 12,10Z";let Te=class extends re{constructor(){super(...arguments),this._devices=[],this._hairDevices=[],this._loading=!0,this._error=null,this._showDismissed=!1,this._expandedId=null,this._expandedDevice=null,this._flashIds=new Set,this._flashStats=new Set,this._recentFingerprints=[],this._glowFingerprints=new Set,this._hitFlashFingerprints=new Set,this._confirmClearAll=!1,this._editingDeviceId=null,this._editLabel="",this._promoteTarget=null,this._assignSignal=null,this._deleteSignal=null,this._testingFingerprint=null,this._testResult=null,this._unsubLive=null,this._unsubRemoved=null}connectedCallback(){super.connectedCallback(),this._load(),this._subscribeLive(),this._subscribeRemoved()}updated(e){if(super.updated(e),e.has("_editingDeviceId")&&this._editingDeviceId){const e=this.shadowRoot?.querySelector(".rename-input");e&&(e.focus(),e.select())}}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeLive(),this._unsubscribeRemoved()}async _load(){this._loading=!0;try{const[e,t]=await Promise.all([this.api.getUnknownDevices({include_dismissed:this._showDismissed}),this.api.listDevices()]);this._devices=e,this._hairDevices=t,this._error=null}catch(e){this._error=`Failed to load: ${e.message}`}finally{this._loading=!1}}_matchesHairDevice(e){if(!e)return!1;const t=e.toLowerCase();return this._hairDevices.some(e=>e.name.toLowerCase()===t)}async _subscribeLive(){try{this._unsubLive=await this.api.subscribeUnknownSignals(e=>{this._onLiveSignal(e)})}catch{}}async _unsubscribeLive(){this._unsubLive&&(await this._unsubLive(),this._unsubLive=null)}async _subscribeRemoved(){try{this._unsubRemoved=await this.api.subscribeSignalRemoved(e=>{this._load(),this._expandedId===e.device_id&&(e.device_removed?(this._expandedId=null,this._expandedDevice=null):(this._toggleExpand(e.device_id),this._toggleExpand(e.device_id)))})}catch{}}async _unsubscribeRemoved(){this._unsubRemoved&&(await this._unsubRemoved(),this._unsubRemoved=null)}_startRename(e,t){t.stopPropagation(),this._editingDeviceId=e.id,this._editLabel=e.label??e.protocol??""}async _commitRename(e){const t=this._editLabel.trim();this._editingDeviceId=null;try{const i=await this.api.renameUnknown(e,t),s=this._devices.findIndex(t=>t.id===e);if(s>=0){const e=[...this._devices];e[s]={...e[s],label:i.label},this._devices=e}}catch(e){this._error=`Rename failed: ${e.message}`}}_cancelRename(){this._editingDeviceId=null}_onRenameKeydown(e,t){"Enter"===t.key?this._commitRename(e):"Escape"===t.key&&this._cancelRename()}_promoteDevice(e,t){t.stopPropagation(),this._promoteTarget=e}_closePromote(){this._promoteTarget=null}async _onDevicePromoted(){this._promoteTarget=null,await this._load()}_openAssign(e,t,i,s){this._assignSignal={deviceId:e,signal:t,label:i??null,initialMode:s??"existing"}}_closeAssign(){this._assignSignal=null}async _onSignalAssigned(e){if(this._assignSignal=null,await this._load(),this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{this._expandedId=null,this._expandedDevice=null}}_openDelete(e,t){this._deleteSignal={deviceId:e,signal:t}}_closeDelete(){this._deleteSignal=null}async _confirmDelete(){if(!this._deleteSignal)return;const{deviceId:e,signal:t}=this._deleteSignal;this._deleteSignal=null;try{await this.api.deleteSignal(e,t.fingerprint),await this._load()}catch(e){this._error=`Delete failed: ${e.message}`}}async _testSignalInline(e,t){this._testingFingerprint=e.fingerprint,this._testResult=null;try{const t=await this.api.testSignal(e.fingerprint);this._testResult=t.sent?"Sent!":"Failed"}catch{this._testResult="Error"}setTimeout(()=>{this._testResult=null,this._testingFingerprint=null},3e3)}_onLiveSignal(e){const t=(new Date).toISOString(),i=this._devices.findIndex(t=>t.id===e.device_id);if(i>=0){{const s={...this._devices[i]};s.hit_count=e.device_hit_count??e.hit_count,s.last_seen=t;const a=[...this._devices];a[i]=s,this._devices=a}if(this._expandedDevice&&this._expandedId===e.device_id){const i=this._expandedDevice.signals.findIndex(t=>t.fingerprint===e.signal_fingerprint);if(i>=0){const s={...this._expandedDevice.signals[i]};s.hit_count=e.hit_count,s.last_seen=t;const a=[...this._expandedDevice.signals];a[i]=s,this._expandedDevice={...this._expandedDevice,hit_count:e.device_hit_count??e.hit_count,last_seen:t,signals:a}}else this.api.getUnknownDevice(e.device_id).then(t=>{this._expandedId===e.device_id&&(this._expandedDevice=t)}).catch(()=>{})}if(this._flashIds=new Set([...this._flashIds,e.device_id]),setTimeout(()=>{const t=new Set(this._flashIds);t.delete(e.device_id),this._flashIds=t},800),this._flashStats=new Set([...this._flashStats,e.device_id]),setTimeout(()=>{const t=new Set(this._flashStats);t.delete(e.device_id),this._flashStats=t},1500),e.signal_fingerprint){const t=[e.signal_fingerprint,...this._recentFingerprints.filter(t=>t!==e.signal_fingerprint)].slice(0,2);this._recentFingerprints=t,this._glowFingerprints=new Set([...this._glowFingerprints,e.signal_fingerprint]),setTimeout(()=>{const t=new Set(this._glowFingerprints);t.delete(e.signal_fingerprint),this._glowFingerprints=t},1200),this._hitFlashFingerprints=new Set([...this._hitFlashFingerprints,e.signal_fingerprint]),setTimeout(()=>{const t=new Set(this._hitFlashFingerprints);t.delete(e.signal_fingerprint),this._hitFlashFingerprints=t},1200)}}else this._load()}async _toggleExpand(e){if(this._expandedId===e)return this._expandedId=null,void(this._expandedDevice=null);this._expandedId=e;try{this._expandedDevice=await this.api.getUnknownDevice(e)}catch{this._expandedDevice=null}}async _dismiss(e){try{await this.api.dismissUnknown(e),await this._load(),this._expandedId===e&&(this._expandedId=null,this._expandedDevice=null)}catch(e){this._error=`Dismiss failed: ${e.message}`}}async _undismiss(e){try{await this.api.undismissUnknown(e),await this._load()}catch(e){this._error=`Restore failed: ${e.message}`}}async _doClearAll(){this._confirmClearAll=!1;try{await this.api.clearUnknowns(),this._devices=[],this._expandedId=null,this._expandedDevice=null}catch(e){this._error=`Clear failed: ${e.message}`}}_toggleDismissed(){this._showDismissed=!this._showDismissed,this._load()}render(){return F`
            <div class="toolbar">
                <span class="title">
                    <ha-svg-icon .path=${Ne}></ha-svg-icon>
                    HAIR Sniffer
                    ${this._loading?"":F`<span class="count">(${this._devices.length})</span>`}
                </span>
                <div class="toolbar-actions">
                    <button
                        class="action-btn dismiss-btn"
                        @click=${this._toggleDismissed}
                    >${this._showDismissed?"Hide Dismissed":"Show Dismissed"}</button>
                    ${this._devices.length>0?F`
                              <button
                                  class="action-btn delete-btn"
                                  @click=${()=>this._confirmClearAll=!0}
                              >Clear All</button>
                          `:""}
                </div>
            </div>

            ${this._error?F`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

            ${this._loading?F`<div class="loading">Scanning for signals...</div>`:0===this._devices.length?F`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${Ne}></ha-svg-icon>
                            <h3>No unknown signals detected</h3>
                            <p>
                                When unrecognized IR signals are received by your
                                ESPHome devices, they will appear here automatically.
                            </p>
                            <p class="hint">
                                Try pressing a button on a remote that hasn't been
                                configured yet.
                            </p>
                        </ha-card>
                    `:F`
                        <div class="device-list">
                            ${this._devices.map(e=>this._renderDevice(e))}
                        </div>
                    `}

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
                          title="Delete Signal"
                          message="Remove this signal permanently? This cannot be undone."
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._confirmDelete}
                          @closed=${this._closeDelete}
                      ></ir-confirm-dialog>
                  `:""}

            ${this._confirmClearAll?F`
                      <ir-confirm-dialog
                          title="Clear All Signals"
                          message="Remove all unknown signals and devices? This cannot be undone."
                          confirmLabel="Clear All"
                          .destructive=${!0}
                          @confirmed=${this._doClearAll}
                          @closed=${()=>this._confirmClearAll=!1}
                      ></ir-confirm-dialog>
                  `:""}
        `}_renderDevice(e){const t=this._expandedId===e.id,i=this._flashIds.has(e.id),s=this._flashStats.has(e.id);return F`
            <ha-card class="device ${i?"flash":""} ${e.dismissed?"dismissed":""}">
                <div
                    class="device-row"
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
                                  />`:F`<span
                                      class="protocol"
                                      title="Click to rename"
                                      @click=${t=>this._startRename(e,t)}
                                  >${e.label??e.protocol??"RAW"}</span>
                                  <ha-svg-icon
                                      class="edit-icon"
                                      .path=${"M14.06,9L15,9.94L5.92,19H5V18.08L14.06,9M17.66,3C17.41,3 17.15,3.1 16.96,3.29L15.13,5.12L18.88,8.87L20.71,7.04C21.1,6.65 21.1,6.02 20.71,5.63L18.37,3.29C18.17,3.09 17.92,3 17.66,3M14.06,6.19L3,17.25V21H6.75L17.81,9.94L14.06,6.19Z"}
                                      title="Rename"
                                      @click=${t=>this._startRename(e,t)}
                                  ></ha-svg-icon>`}
                            ${e.device_address?F`<span class="address">addr: ${e.device_address}</span>`:""}
                            ${e.dismissed?F`<span class="dismissed-badge">dismissed</span>`:""}
                        </div>
                        <div class="device-stats ${s?"stats-flash":""}">
                            <span class="stat">
                                <strong>${e.hit_count}</strong> hits
                            </span>
                            <span class="stat">
                                <strong>${e.signal_count}</strong> signals
                            </span>
                            <span class="stat last-seen" title=${Ie(e.last_seen)}>
                                ${Pe(e.last_seen)}
                            </span>
                        </div>
                    </div>
                    ${e.label&&this._matchesHairDevice(e.label)?F`<span
                              class="status-badge hair-device"
                              @click=${e=>e.stopPropagation()}
                          >HAIR Device</span>`:e.label?F`<button
                                  class="action-btn promote-btn"
                                  @click=${t=>this._promoteDevice(e,t)}
                              >Promote to Device</button>`:""}
                    <ha-svg-icon
                        class="expand-icon"
                        .path=${t?"M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z":"M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z"}
                    ></ha-svg-icon>
                </div>

                ${t&&this._expandedDevice?this._renderExpanded(this._expandedDevice,e.dismissed):""}
            </ha-card>
        `}_renderExpanded(e,t){return F`
            <div class="expanded">
                <div class="signal-header">
                    <span>Signals (${e.signals.length})</span>
                    <span class="first-seen">First seen: ${Ie(e.first_seen)}</span>
                </div>
                <div class="signal-list">
                    ${e.signals.map(i=>{const s=this._recentFingerprints.indexOf(i.fingerprint),a=0===s,o=1===s,n=this._glowFingerprints.has(i.fingerprint),r=this._hitFlashFingerprints.has(i.fingerprint);return F`
                            <div class="signal-row">
                                <div class="signal-info">
                                    ${i.sl_pattern?F`<span class="diamonds">${[...i.sl_pattern].map(e=>"L"===e?F`<span class="diamond long">◆</span>`:F`<span class="diamond short">◇</span>`)}</span>`:F`<code class="signal-code">${i.protocol??"RAW"}: ${i.code??`${i.raw_timings.length} timings`}</code>`}
                                </div>
                                <div class="signal-meta">
                                    <span class="${r?"hit-flash":""}">${i.hit_count} hits</span>
                                    <span title=${Ie(i.last_seen)}
                                        >${Pe(i.last_seen)}</span
                                    >
                                </div>
                                <div class="signal-actions">
                                    <button
                                        class="action-btn assign-btn ${a?"recent-latest":""} ${o?"recent-previous":""} ${n?"glow":""}"
                                        @click=${t=>{t.stopPropagation(),this._openAssign(e.id,i,e.label)}}
                                    >Assign</button>
                                    <button
                                        class="action-btn test-btn"
                                        @click=${t=>{t.stopPropagation(),this._testSignalInline(i,e.id)}}
                                        ?disabled=${this._testingFingerprint===i.fingerprint}
                                    >${this._testingFingerprint===i.fingerprint?this._testResult??"Sending...":"Test"}</button>
                                    <button
                                        class="action-btn delete-btn"
                                        @click=${t=>{t.stopPropagation(),this._openDelete(e.id,i)}}
                                    >Delete</button>
                                    ${t?F`<button
                                              class="action-btn"
                                              @click=${t=>{t.stopPropagation(),this._undismiss(e.id)}}
                                          >Restore</button>`:F`<button
                                              class="action-btn dismiss-btn"
                                              @click=${t=>{t.stopPropagation(),this._dismiss(e.id)}}
                                          >Dismiss</button>`}
                                </div>
                            </div>
                        `})}
                </div>
            </div>
        `}};Te.styles=n`
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
        }
        .device.flash {
            box-shadow: 0 0 0 2px var(--primary-color), var(--ha-card-box-shadow, none);
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
        .protocol:hover {
            border-bottom-color: var(--primary-color);
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
        .status-badge.hair-device {
            font-size: 0.75rem;
            font-weight: 500;
            font-family: inherit;
            padding: 4px 10px;
            border-radius: 4px;
            white-space: nowrap;
            flex-shrink: 0;
            background: rgba(46, 125, 50, 0.15);
            color: #2e7d32;
            border: 1px solid rgba(46, 125, 50, 0.3);
        }
        .promote-btn {
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
            display: flex;
            gap: 16px;
            margin-top: 4px;
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
            background: var(--secondary-background-color);
            border-radius: 4px;
            gap: 8px;
            flex-wrap: wrap;
        }
        .signal-info {
            flex: 1;
            min-width: 0;
        }
        .signal-code {
            font-size: 0.82rem;
            word-break: break-all;
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

        /* Semantic button colors */
        .action-btn.assign-btn {
            color: #2e7d32;
            border-color: rgba(46, 125, 50, 0.3);
        }
        .action-btn.assign-btn:hover {
            background: rgba(46, 125, 50, 0.08);
        }
        .action-btn.test-btn {
            color: var(--primary-color);
        }
        .action-btn.delete-btn {
            color: #b71c1c;
            border-color: rgba(183, 28, 28, 0.2);
        }
        .action-btn.delete-btn:hover {
            background: rgba(183, 28, 28, 0.06);
        }
        .action-btn.dismiss-btn {
            color: var(--secondary-text-color);
            border-color: var(--divider-color);
        }

        /* Latest signal: bright green filled Assign button */
        .action-btn.assign-btn.recent-latest {
            color: #fff;
            background: #2e7d32;
            border-color: #2e7d32;
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

        /* Glow pulse animation on hit */
        .action-btn.assign-btn.glow {
            animation: assign-glow 1.2s ease-out;
        }
        @keyframes assign-glow {
            0% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0.6); }
            50% { box-shadow: 0 0 8px 3px rgba(46, 125, 50, 0.3); }
            100% { box-shadow: 0 0 0 0 rgba(46, 125, 50, 0); }
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
    `,e([pe({attribute:!1})],Te.prototype,"api",void 0),e([pe({attribute:!1})],Te.prototype,"hass",void 0),e([ue()],Te.prototype,"_devices",void 0),e([ue()],Te.prototype,"_hairDevices",void 0),e([ue()],Te.prototype,"_loading",void 0),e([ue()],Te.prototype,"_error",void 0),e([ue()],Te.prototype,"_showDismissed",void 0),e([ue()],Te.prototype,"_expandedId",void 0),e([ue()],Te.prototype,"_expandedDevice",void 0),e([ue()],Te.prototype,"_flashIds",void 0),e([ue()],Te.prototype,"_flashStats",void 0),e([ue()],Te.prototype,"_recentFingerprints",void 0),e([ue()],Te.prototype,"_glowFingerprints",void 0),e([ue()],Te.prototype,"_hitFlashFingerprints",void 0),e([ue()],Te.prototype,"_confirmClearAll",void 0),e([ue()],Te.prototype,"_editingDeviceId",void 0),e([ue()],Te.prototype,"_editLabel",void 0),e([ue()],Te.prototype,"_promoteTarget",void 0),e([ue()],Te.prototype,"_assignSignal",void 0),e([ue()],Te.prototype,"_deleteSignal",void 0),e([ue()],Te.prototype,"_testingFingerprint",void 0),e([ue()],Te.prototype,"_testResult",void 0),Te=e([ce("ir-signal-monitor")],Te);let Me=class extends re{constructor(){super(...arguments),this.narrow=!1,this._activeTab="devices",this._devices=[],this._expandedDeviceId=null,this._loading=!0,this._error=null,this._addDialogOpen=!1,this._api=null}connectedCallback(){super.connectedCallback(),this.hass&&this._init()}updated(e){e.has("hass")&&this.hass&&!this._api&&this._init()}_init(){this._api=new ve(this.hass),this._refreshDevices()}async _refreshDevices(){if(this._api){this._loading=!0;try{this._devices=await this._api.listDevices(),this._error=null}catch(e){this._error=`Failed to load devices: ${e.message}`}finally{this._loading=!1}}}_toggleDevice(e){this._expandedDeviceId=this._expandedDeviceId===e?null:e}_openAddDialog(){this._addDialogOpen=!0}_closeAddDialog(){this._addDialogOpen=!1}async _onDeviceCreated(e){this._addDialogOpen=!1,await this._refreshDevices(),this._expandedDeviceId=e.detail.id}async _onDeviceChanged(){await this._refreshDevices()}async _onDeviceDeleted(){this._expandedDeviceId=null,await this._refreshDevices()}_switchTab(e){this._expandedDeviceId=null,this._activeTab=e,"devices"===e&&this._refreshDevices()}render(){return this._api?F`
            <ha-top-app-bar-fixed>
                <ha-icon-button
                    slot="navigationIcon"
                    .path=${"M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z"}
                ></ha-icon-button>
                <span slot="title">HAIR</span>
            </ha-top-app-bar-fixed>

            <div class="tab-bar">
                <button
                    class="tab ${"devices"===this._activeTab?"active":""}"
                    @click=${()=>this._switchTab("devices")}
                >
                    Devices
                </button>
                <button
                    class="tab ${"sniffer"===this._activeTab?"active":""}"
                    @click=${()=>this._switchTab("sniffer")}
                >
                    Sniffer
                </button>
            </div>

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
                              @add-device=${this._openAddDialog}
                          ></ir-device-list>

                          ${!this._loading&&this._devices.length>0?F`
                                    <ha-fab
                                        class="fab"
                                        label="Add Device"
                                        extended
                                        @click=${this._openAddDialog}
                                    >
                                        <ha-svg-icon
                                            slot="icon"
                                            .path=${"M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z"}
                                        ></ha-svg-icon>
                                    </ha-fab>
                                `:""}
                      `:F`
                          <ir-signal-monitor
                              .api=${this._api}
                              .hass=${this.hass}
                          ></ir-signal-monitor>
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
        `:F`<div class="loading">Loading…</div>`}};Me.styles=n`
        :host {
            display: block;
            background: var(--primary-background-color);
            color: var(--primary-text-color);
            min-height: 100vh;
        }
        .tab-bar {
            display: flex;
            border-bottom: 1px solid var(--divider-color);
            padding: 0 16px;
            max-width: 1100px;
            margin: 0 auto;
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
        .fab {
            position: fixed;
            right: 24px;
            bottom: 24px;
        }
    `,e([pe({attribute:!1})],Me.prototype,"hass",void 0),e([pe({attribute:!1})],Me.prototype,"narrow",void 0),e([pe({attribute:!1})],Me.prototype,"route",void 0),e([pe({attribute:!1})],Me.prototype,"panel",void 0),e([ue()],Me.prototype,"_activeTab",void 0),e([ue()],Me.prototype,"_devices",void 0),e([ue()],Me.prototype,"_expandedDeviceId",void 0),e([ue()],Me.prototype,"_loading",void 0),e([ue()],Me.prototype,"_error",void 0),e([ue()],Me.prototype,"_addDialogOpen",void 0),Me=e([ce("ha-panel-ir-devices")],Me);export{Me as HaPanelIrDevices};
