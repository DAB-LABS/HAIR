function e(e,t,i,s){var a,o=arguments.length,n=o<3?t:null===s?s=Object.getOwnPropertyDescriptor(t,i):s;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)n=Reflect.decorate(e,t,i,s);else for(var r=e.length-1;r>=0;r--)(a=e[r])&&(n=(o<3?a(n):o>3?a(t,i,n):a(t,i))||n);return o>3&&n&&Object.defineProperty(t,i,n),n}"function"==typeof SuppressedError&&SuppressedError;const t=globalThis,i=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,s=Symbol(),a=new WeakMap;let o=class{constructor(e,t,i){if(this._$cssResult$=!0,i!==s)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(i&&void 0===e){const i=void 0!==t&&1===t.length;i&&(e=a.get(t)),void 0===e&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),i&&a.set(t,e))}return e}toString(){return this.cssText}};const n=(e,...t)=>{const i=1===e.length?e[0]:t.reduce((t,i,s)=>t+(e=>{if(!0===e._$cssResult$)return e.cssText;if("number"==typeof e)return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+e[s+1],e[0]);return new o(i,e,s)},r=i?e=>e:e=>e instanceof CSSStyleSheet?(e=>{let t="";for(const i of e.cssRules)t+=i.cssText;return(e=>new o("string"==typeof e?e:e+"",void 0,s))(t)})(e):e,{is:c,defineProperty:d,getOwnPropertyDescriptor:l,getOwnPropertyNames:h,getOwnPropertySymbols:p,getPrototypeOf:u}=Object,m=globalThis,v=m.trustedTypes,_=v?v.emptyScript:"",g=m.reactiveElementPolyfillSupport,y=(e,t)=>e,b={toAttribute(e,t){switch(t){case Boolean:e=e?_:null;break;case Object:case Array:e=null==e?e:JSON.stringify(e)}return e},fromAttribute(e,t){let i=e;switch(t){case Boolean:i=null!==e;break;case Number:i=null===e?null:Number(e);break;case Object:case Array:try{i=JSON.parse(e)}catch(e){i=null}}return i}},$=(e,t)=>!c(e,t),f={attribute:!0,type:String,converter:b,reflect:!1,useDefault:!1,hasChanged:$};Symbol.metadata??=Symbol("metadata"),m.litPropertyMetadata??=new WeakMap;let w=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=f){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const i=Symbol(),s=this.getPropertyDescriptor(e,i,t);void 0!==s&&d(this.prototype,e,s)}}static getPropertyDescriptor(e,t,i){const{get:s,set:a}=l(this.prototype,e)??{get(){return this[t]},set(e){this[t]=e}};return{get:s,set(t){const o=s?.call(this);a?.call(this,t),this.requestUpdate(e,o,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??f}static _$Ei(){if(this.hasOwnProperty(y("elementProperties")))return;const e=u(this);e.finalize(),void 0!==e.l&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(y("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(y("properties"))){const e=this.properties,t=[...h(e),...p(e)];for(const i of t)this.createProperty(i,e[i])}const e=this[Symbol.metadata];if(null!==e){const t=litPropertyMetadata.get(e);if(void 0!==t)for(const[e,i]of t)this.elementProperties.set(e,i)}this._$Eh=new Map;for(const[e,t]of this.elementProperties){const i=this._$Eu(e,t);void 0!==i&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const i=new Set(e.flat(1/0).reverse());for(const e of i)t.unshift(r(e))}else void 0!==e&&t.push(r(e));return t}static _$Eu(e,t){const i=t.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof e?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),void 0!==this.renderRoot&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const i of t.keys())this.hasOwnProperty(i)&&(e.set(i,this[i]),delete this[i]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((e,s)=>{if(i)e.adoptedStyleSheets=s.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(const i of s){const s=document.createElement("style"),a=t.litNonce;void 0!==a&&s.setAttribute("nonce",a),s.textContent=i.cssText,e.appendChild(s)}})(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,i){this._$AK(e,i)}_$ET(e,t){const i=this.constructor.elementProperties.get(e),s=this.constructor._$Eu(e,i);if(void 0!==s&&!0===i.reflect){const a=(void 0!==i.converter?.toAttribute?i.converter:b).toAttribute(t,i.type);this._$Em=e,null==a?this.removeAttribute(s):this.setAttribute(s,a),this._$Em=null}}_$AK(e,t){const i=this.constructor,s=i._$Eh.get(e);if(void 0!==s&&this._$Em!==s){const e=i.getPropertyOptions(s),a="function"==typeof e.converter?{fromAttribute:e.converter}:void 0!==e.converter?.fromAttribute?e.converter:b;this._$Em=s;const o=a.fromAttribute(t,e.type);this[s]=o??this._$Ej?.get(s)??o,this._$Em=null}}requestUpdate(e,t,i,s=!1,a){if(void 0!==e){const o=this.constructor;if(!1===s&&(a=this[e]),i??=o.getPropertyOptions(e),!((i.hasChanged??$)(a,t)||i.useDefault&&i.reflect&&a===this._$Ej?.get(e)&&!this.hasAttribute(o._$Eu(e,i))))return;this.C(e,t,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(e,t,{useDefault:i,reflect:s,wrapped:a},o){i&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,o??t??this[e]),!0!==a||void 0!==o)||(this._$AL.has(e)||(this.hasUpdated||i||(t=void 0),this._$AL.set(e,t)),!0===s&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}const e=this.scheduleUpdate();return null!=e&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[e,t]of this._$Ep)this[e]=t;this._$Ep=void 0}const e=this.constructor.elementProperties;if(e.size>0)for(const[t,i]of e){const{wrapped:e}=i,s=this[t];!0!==e||this._$AL.has(t)||void 0===s||this.C(t,void 0,i,s)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(e=>e.hostUpdate?.()),this.update(t)):this._$EM()}catch(t){throw e=!1,this._$EM(),t}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(e){}firstUpdated(e){}};w.elementStyles=[],w.shadowRootOptions={mode:"open"},w[y("elementProperties")]=new Map,w[y("finalized")]=new Map,g?.({ReactiveElement:w}),(m.reactiveElementVersions??=[]).push("2.1.2");const x=globalThis,C=e=>e,A=x.trustedTypes,D=A?A.createPolicy("lit-html",{createHTML:e=>e}):void 0,k="$lit$",E=`lit$${Math.random().toFixed(9).slice(2)}$`,S="?"+E,M=`<${S}>`,P=document,L=()=>P.createComment(""),H=e=>null===e||"object"!=typeof e&&"function"!=typeof e,N=Array.isArray,T="[ \t\n\f\r]",I=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,R=/-->/g,O=/>/g,U=RegExp(`>|${T}(?:([^\\s"'>=/]+)(${T}*=${T}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),V=/'/g,z=/"/g,j=/^(?:script|style|textarea|title)$/i,B=(e,...t)=>({_$litType$:1,strings:e,values:t}),Z=Symbol.for("lit-noChange"),W=Symbol.for("lit-nothing"),q=new WeakMap,Q=P.createTreeWalker(P,129);function F(e,t){if(!N(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==D?D.createHTML(t):t}const J=(e,t)=>{const i=e.length-1,s=[];let a,o=2===t?"<svg>":3===t?"<math>":"",n=I;for(let t=0;t<i;t++){const i=e[t];let r,c,d=-1,l=0;for(;l<i.length&&(n.lastIndex=l,c=n.exec(i),null!==c);)l=n.lastIndex,n===I?"!--"===c[1]?n=R:void 0!==c[1]?n=O:void 0!==c[2]?(j.test(c[2])&&(a=RegExp("</"+c[2],"g")),n=U):void 0!==c[3]&&(n=U):n===U?">"===c[0]?(n=a??I,d=-1):void 0===c[1]?d=-2:(d=n.lastIndex-c[2].length,r=c[1],n=void 0===c[3]?U:'"'===c[3]?z:V):n===z||n===V?n=U:n===R||n===O?n=I:(n=U,a=void 0);const h=n===U&&e[t+1].startsWith("/>")?" ":"";o+=n===I?i+M:d>=0?(s.push(r),i.slice(0,d)+k+i.slice(d)+E+h):i+E+(-2===d?t:h)}return[F(e,o+(e[i]||"<?>")+(2===t?"</svg>":3===t?"</math>":"")),s]};class K{constructor({strings:e,_$litType$:t},i){let s;this.parts=[];let a=0,o=0;const n=e.length-1,r=this.parts,[c,d]=J(e,t);if(this.el=K.createElement(c,i),Q.currentNode=this.el.content,2===t||3===t){const e=this.el.content.firstChild;e.replaceWith(...e.childNodes)}for(;null!==(s=Q.nextNode())&&r.length<n;){if(1===s.nodeType){if(s.hasAttributes())for(const e of s.getAttributeNames())if(e.endsWith(k)){const t=d[o++],i=s.getAttribute(e).split(E),n=/([.?@])?(.*)/.exec(t);r.push({type:1,index:a,name:n[2],strings:i,ctor:"."===n[1]?te:"?"===n[1]?ie:"@"===n[1]?se:ee}),s.removeAttribute(e)}else e.startsWith(E)&&(r.push({type:6,index:a}),s.removeAttribute(e));if(j.test(s.tagName)){const e=s.textContent.split(E),t=e.length-1;if(t>0){s.textContent=A?A.emptyScript:"";for(let i=0;i<t;i++)s.append(e[i],L()),Q.nextNode(),r.push({type:2,index:++a});s.append(e[t],L())}}}else if(8===s.nodeType)if(s.data===S)r.push({type:2,index:a});else{let e=-1;for(;-1!==(e=s.data.indexOf(E,e+1));)r.push({type:7,index:a}),e+=E.length-1}a++}}static createElement(e,t){const i=P.createElement("template");return i.innerHTML=e,i}}function Y(e,t,i=e,s){if(t===Z)return t;let a=void 0!==s?i._$Co?.[s]:i._$Cl;const o=H(t)?void 0:t._$litDirective$;return a?.constructor!==o&&(a?._$AO?.(!1),void 0===o?a=void 0:(a=new o(e),a._$AT(e,i,s)),void 0!==s?(i._$Co??=[])[s]=a:i._$Cl=a),void 0!==a&&(t=Y(e,a._$AS(e,t.values),a,s)),t}class X{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:i}=this._$AD,s=(e?.creationScope??P).importNode(t,!0);Q.currentNode=s;let a=Q.nextNode(),o=0,n=0,r=i[0];for(;void 0!==r;){if(o===r.index){let t;2===r.type?t=new G(a,a.nextSibling,this,e):1===r.type?t=new r.ctor(a,r.name,r.strings,this,e):6===r.type&&(t=new ae(a,this,e)),this._$AV.push(t),r=i[++n]}o!==r?.index&&(a=Q.nextNode(),o++)}return Q.currentNode=P,s}p(e){let t=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(e,i,t),t+=i.strings.length-2):i._$AI(e[t])),t++}}class G{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,i,s){this.type=2,this._$AH=W,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=i,this.options=s,this._$Cv=s?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return void 0!==t&&11===e?.nodeType&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=Y(this,e,t),H(e)?e===W||null==e||""===e?(this._$AH!==W&&this._$AR(),this._$AH=W):e!==this._$AH&&e!==Z&&this._(e):void 0!==e._$litType$?this.$(e):void 0!==e.nodeType?this.T(e):(e=>N(e)||"function"==typeof e?.[Symbol.iterator])(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==W&&H(this._$AH)?this._$AA.nextSibling.data=e:this.T(P.createTextNode(e)),this._$AH=e}$(e){const{values:t,_$litType$:i}=e,s="number"==typeof i?this._$AC(e):(void 0===i.el&&(i.el=K.createElement(F(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===s)this._$AH.p(t);else{const e=new X(s,this),i=e.u(this.options);e.p(t),this.T(i),this._$AH=e}}_$AC(e){let t=q.get(e.strings);return void 0===t&&q.set(e.strings,t=new K(e)),t}k(e){N(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let i,s=0;for(const a of e)s===t.length?t.push(i=new G(this.O(L()),this.O(L()),this,this.options)):i=t[s],i._$AI(a),s++;s<t.length&&(this._$AR(i&&i._$AB.nextSibling,s),t.length=s)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){const t=C(e).nextSibling;C(e).remove(),e=t}}setConnected(e){void 0===this._$AM&&(this._$Cv=e,this._$AP?.(e))}}class ee{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,i,s,a){this.type=1,this._$AH=W,this._$AN=void 0,this.element=e,this.name=t,this._$AM=s,this.options=a,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=W}_$AI(e,t=this,i,s){const a=this.strings;let o=!1;if(void 0===a)e=Y(this,e,t,0),o=!H(e)||e!==this._$AH&&e!==Z,o&&(this._$AH=e);else{const s=e;let n,r;for(e=a[0],n=0;n<a.length-1;n++)r=Y(this,s[i+n],t,n),r===Z&&(r=this._$AH[n]),o||=!H(r)||r!==this._$AH[n],r===W?e=W:e!==W&&(e+=(r??"")+a[n+1]),this._$AH[n]=r}o&&!s&&this.j(e)}j(e){e===W?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class te extends ee{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===W?void 0:e}}class ie extends ee{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==W)}}class se extends ee{constructor(e,t,i,s,a){super(e,t,i,s,a),this.type=5}_$AI(e,t=this){if((e=Y(this,e,t,0)??W)===Z)return;const i=this._$AH,s=e===W&&i!==W||e.capture!==i.capture||e.once!==i.once||e.passive!==i.passive,a=e!==W&&(i===W||s);s&&this.element.removeEventListener(this.name,this,i),a&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}}class ae{constructor(e,t,i){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(e){Y(this,e)}}const oe=x.litHtmlPolyfillSupport;oe?.(K,G),(x.litHtmlVersions??=[]).push("3.3.2");const ne=globalThis;class re extends w{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=((e,t,i)=>{const s=i?.renderBefore??t;let a=s._$litPart$;if(void 0===a){const e=i?.renderBefore??null;s._$litPart$=a=new G(t.insertBefore(L(),e),e,void 0,i??{})}return a._$AI(e),a})(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return Z}}re._$litElement$=!0,re.finalized=!0,ne.litElementHydrateSupport?.({LitElement:re});const ce=ne.litElementPolyfillSupport;ce?.({LitElement:re}),(ne.litElementVersions??=[]).push("4.2.2");const de=e=>(t,i)=>{void 0!==i?i.addInitializer(()=>{customElements.define(e,t)}):customElements.define(e,t)},le={attribute:!0,type:String,converter:b,reflect:!1,hasChanged:$},he=(e=le,t,i)=>{const{kind:s,metadata:a}=i;let o=globalThis.litPropertyMetadata.get(a);if(void 0===o&&globalThis.litPropertyMetadata.set(a,o=new Map),"setter"===s&&((e=Object.create(e)).wrapped=!0),o.set(i.name,e),"accessor"===s){const{name:s}=i;return{set(i){const a=t.get.call(this);t.set.call(this,i),this.requestUpdate(s,a,e,!0,i)},init(t){return void 0!==t&&this.C(s,void 0,e,t),t}}}if("setter"===s){const{name:s}=i;return function(i){const a=this[s];t.call(this,i),this.requestUpdate(s,a,e,!0,i)}}throw Error("Unsupported decorator location: "+s)};function pe(e){return(t,i)=>"object"==typeof i?he(e,t,i):((e,t,i)=>{const s=t.hasOwnProperty(i);return t.constructor.createProperty(i,e),s?Object.getOwnPropertyDescriptor(t,i):void 0})(e,t,i)}function ue(e){return pe({...e,state:!0,attribute:!1})}class me{constructor(e){this.hass=e}listDevices(){return this.hass.connection.sendMessagePromise({type:"hair/devices"})}getDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/device",device_id:e})}createDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/device/create",...e})}updateDevice(e,t){return this.hass.connection.sendMessagePromise({type:"hair/device/update",device_id:e,...t})}deleteDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/device/delete",device_id:e})}deleteCommand(e,t){return this.hass.connection.sendMessagePromise({type:"hair/command/delete",device_id:e,command_id:t})}sendCommand(e,t){return this.hass.connection.sendMessagePromise({type:"hair/command/send",device_id:e,command_id:t})}listTemplates(e){return this.hass.connection.sendMessagePromise({type:"hair/templates",device_type:e})}listCaptureProviders(){return this.hass.connection.sendMessagePromise({type:"hair/capture/providers"})}async startCapture(e,t,i){let s=null;const a=await this.hass.connection.subscribeMessage(e=>{e.type?.startsWith("capture_")?i(e):e.session_id&&(s=e)},{type:"hair/capture/start",device_id:e,timeout:t});if(await Promise.resolve(),null===s)throw new Error("Capture session did not start");return{session:s,unsubscribe:a}}cancelCapture(e){return this.hass.connection.sendMessagePromise({type:"hair/capture/cancel",session_id:e})}saveCapturedCommand(e){return this.hass.connection.sendMessagePromise({type:"hair/capture/save",...e})}getUnknownDevices(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/devices",...e})}getUnknownDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/device",device_id:e})}dismissUnknown(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/dismiss",device_id:e})}undismissUnknown(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/undismiss",device_id:e})}assignSignal(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/assign",...e})}assignToNewDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/assign-new-device",...e})}deleteSignal(e,t){return this.hass.connection.sendMessagePromise({type:"hair/unknown/signal/delete",device_id:e,signal_fingerprint:t})}testSignal(e,t){return this.hass.connection.sendMessagePromise({type:"hair/unknown/test",signal_fingerprint:e,emitter_entity_id:t})}clearUnknowns(){return this.hass.connection.sendMessagePromise({type:"hair/unknown/clear"})}async subscribeUnknownSignals(e){return this.hass.connection.subscribeEvents(t=>e(t.data),"hair_signal_detected")}async subscribeSignalRemoved(e){return this.hass.connection.subscribeEvents(t=>e(t.data),"hair_signal_removed")}}const ve={tv:"M21,17H3V5H21M21,3H3A2,2 0 0,0 1,5V17A2,2 0 0,0 3,19H8V21H16V19H21A2,2 0 0,0 23,17V5A2,2 0 0,0 21,3Z",ac:"M11,21H13V11.85L14.6,13.5L16,12.05L12,8L8,12.05L9.4,13.5L11,11.85V21M2,3V11C2,12.66 5.69,14 12,14C18.31,14 22,12.66 22,11V3H2M4,5H20V8.5C18.5,9.27 15.6,10 12,10C8.4,10 5.5,9.27 4,8.5V5Z",fan:"M12,11A1,1 0 0,0 11,12A1,1 0 0,0 12,13A1,1 0 0,0 13,12A1,1 0 0,0 12,11M12.5,2C17,2 17.11,5.57 14.75,6.75C13.76,7.24 13.32,8.29 13.13,9.22C13.61,9.42 14.03,9.73 14.35,10.13C18.05,8.13 22.03,8.92 22.03,12.5C22.03,17 18.46,17.1 17.28,14.73C16.78,13.74 15.72,13.3 14.79,13.11C14.59,13.59 14.28,14 13.88,14.34C15.87,18.03 15.08,22 11.5,22C7,22 6.91,18.42 9.27,17.24C10.25,16.75 10.69,15.71 10.89,14.79C10.4,14.59 9.97,14.27 9.65,13.87C5.96,15.85 2,15.07 2,11.5C2,7 5.56,6.89 6.74,9.26C7.24,10.25 8.29,10.68 9.22,10.87C9.41,10.39 9.73,9.97 10.14,9.65C8.15,5.95 8.94,2 12.5,2Z",soundbar:"M16,4V8H8V4H16M3,9V14H21V9H3M2,16C2,17.1 2.9,18 4,18H20C21.1,18 22,17.1 22,16V8C22,6.89 21.1,6 20,6H4C2.89,6 2,6.89 2,8V16Z",projector:"M4,5A2,2 0 0,0 2,7V17A2,2 0 0,0 4,19H10V21H14V19H20A2,2 0 0,0 22,17V7A2,2 0 0,0 20,5H4M14,8A4,4 0 0,1 18,12A4,4 0 0,1 14,16A4,4 0 0,1 10,12A4,4 0 0,1 14,8M5,9A1,1 0 0,1 6,10A1,1 0 0,1 5,11A1,1 0 0,1 4,10A1,1 0 0,1 5,9M14,10A2,2 0 0,0 12,12A2,2 0 0,0 14,14A2,2 0 0,0 16,12A2,2 0 0,0 14,10Z",other:"M11,2A2,2 0 0,0 9,4V8H4A2,2 0 0,0 2,10V13A2,2 0 0,0 4,15H5V21A2,2 0 0,0 7,23H17A2,2 0 0,0 19,21V15H20A2,2 0 0,0 22,13V10A2,2 0 0,0 20,8H15V4A2,2 0 0,0 13,2H11Z"},_e={tv:"TV",ac:"Air Conditioner",fan:"Fan",soundbar:"Soundbar",projector:"Projector",other:"IR Device"};let ge=class extends re{constructor(){super(...arguments),this.devices=[],this.loading=!1}_select(e){this.dispatchEvent(new CustomEvent("device-selected",{detail:e,bubbles:!0,composed:!0}))}_add(){this.dispatchEvent(new CustomEvent("add-device",{bubbles:!0,composed:!0}))}render(){return this.loading?B`<div class="loading">Loading IR devices…</div>`:0===this.devices.length?B`
                <ha-card class="empty">
                    <h2>No IR devices yet</h2>
                    <p>Add your first device to get started.</p>
                    <mwc-button raised @click=${this._add}>+ Add Device</mwc-button>
                </ha-card>
            `:B`
            <div class="grid">
                ${this.devices.map(e=>B`
                        <ha-card
                            class="device"
                            tabindex="0"
                            @click=${()=>this._select(e.id)}
                            @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._select(e.id))}}
                        >
                            <div class="device-header">
                                <ha-svg-icon
                                    .path=${ve[e.device_type]??ve.other}
                                ></ha-svg-icon>
                                <div class="device-name">${e.name}</div>
                            </div>
                            <div class="device-meta">
                                ${[e.manufacturer,_e[e.device_type],e.emitter_entity_id].filter(Boolean).join(" • ")}
                            </div>
                            <div class="device-footer">
                                <span class="badge"
                                    >${e.command_count} commands</span
                                >
                            </div>
                        </ha-card>
                    `)}
            </div>
        `}};ge.styles=n`
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
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
            gap: 16px;
        }
        .device {
            padding: 16px;
            cursor: pointer;
            transition: transform 120ms ease, box-shadow 120ms ease;
        }
        .device:hover,
        .device:focus-visible {
            transform: translateY(-1px);
            box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0, 0, 0, 0.18));
            outline: 2px solid transparent;
        }
        .device-header {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .device-header ha-svg-icon {
            --mdc-icon-size: 28px;
            color: var(--primary-color);
        }
        .device-name {
            font-size: 1.1rem;
            font-weight: 500;
        }
        .device-meta {
            margin-top: 8px;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
        }
        .device-footer {
            margin-top: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .badge {
            background: var(--secondary-background-color);
            border-radius: 999px;
            padding: 2px 10px;
            font-size: 0.85rem;
        }
    `,e([pe({attribute:!1})],ge.prototype,"devices",void 0),e([pe({type:Boolean})],ge.prototype,"loading",void 0),ge=e([de("ir-device-list")],ge);let ye=class extends re{constructor(){super(...arguments),this.learned=0,this.total=0}render(){const e=this.total>0?this.learned/this.total:0,t=Math.min(100,Math.max(0,Math.round(100*e)));return B`
            <div
                class="bar"
                role="progressbar"
                aria-valuenow=${this.learned}
                aria-valuemax=${this.total}
            >
                <div class="fill" style="width: ${t}%"></div>
            </div>
            <div class="label">${this.learned}/${this.total} commands</div>
        `}};ye.styles=n`
        :host {
            display: block;
            margin: 12px 0 16px;
        }
        .bar {
            background: var(--secondary-background-color);
            border-radius: 4px;
            height: 8px;
            overflow: hidden;
        }
        .fill {
            background: var(--primary-color);
            height: 100%;
            transition: width 200ms ease;
        }
        .label {
            margin-top: 6px;
            font-size: 0.85rem;
            color: var(--secondary-text-color);
        }
    `,e([pe({type:Number})],ye.prototype,"learned",void 0),e([pe({type:Number})],ye.prototype,"total",void 0),ye=e([de("ir-progress-bar")],ye);let be=class extends re{constructor(){super(...arguments),this.templateName="",this.command=null,this.busy=!1}_emit(e){this.dispatchEvent(new CustomEvent(e,{detail:{templateName:this.templateName,command:this.command},bubbles:!0,composed:!0}))}render(){const e=null!==this.command;return B`
            <div class="row" data-learned=${e?"true":"false"}>
                <div class="status" aria-hidden="true">
                    ${e?"✅":"○"}
                </div>
                <div class="info">
                    <div class="name">${this.templateName}</div>
                    <div class="meta">
                        ${e?B`${this.command.protocol??"Raw"} ·
                              ${this.command.code??"timings"}`:B`<span class="muted">Not yet learned</span>`}
                    </div>
                </div>
                <div class="actions">
                    ${e?B`
                              <mwc-button
                                  dense
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("test")}
                              >
                                  ▶ Test
                              </mwc-button>
                              <mwc-button
                                  dense
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("relearn")}
                              >
                                  ↻ Re-learn
                              </mwc-button>
                              <mwc-icon-button
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("delete")}
                                  aria-label="Delete command"
                              >
                                  <ha-svg-icon
                                      .path=${"M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z"}
                                  ></ha-svg-icon>
                              </mwc-icon-button>
                          `:B`
                              <mwc-button
                                  raised
                                  dense
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("learn")}
                              >
                                  Learn
                              </mwc-button>
                          `}
                </div>
            </div>
        `}};be.styles=n`
        :host {
            display: block;
        }
        .row {
            display: grid;
            grid-template-columns: 32px 1fr auto;
            align-items: center;
            gap: 12px;
            padding: 10px 12px;
            border-radius: 8px;
        }
        .row[data-learned="false"] {
            background: var(--secondary-background-color);
        }
        .status {
            font-size: 1.1rem;
            text-align: center;
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
        .actions {
            display: flex;
            gap: 4px;
            align-items: center;
        }
    `,e([pe({attribute:!1})],be.prototype,"templateName",void 0),e([pe({attribute:!1})],be.prototype,"command",void 0),e([pe({type:Boolean})],be.prototype,"busy",void 0),be=e([de("ir-command-row")],be);let $e=class extends re{constructor(){super(...arguments),this.commandName="",this.timeout=15,this._phase="listening",this._result=null,this._duplicate=null,this._error=null,this._timeRemaining=0,this._sessionId=null,this._unsubscribe=null,this._countdown=null}connectedCallback(){super.connectedCallback(),this._beginCapture()}disconnectedCallback(){super.disconnectedCallback(),this._stopCountdown(),this._unsubscribe&&(this._unsubscribe(),this._unsubscribe=null)}async _beginCapture(){this._phase="listening",this._result=null,this._duplicate=null,this._error=null,this._timeRemaining=this.timeout,this._startCountdown();try{const{session:e,unsubscribe:t}=await this.api.startCapture(this.device.id,this.timeout,e=>this._onCaptureEvent(e));this._sessionId=e.session_id,this._unsubscribe=t}catch(e){this._stopCountdown(),this._error=e.message,this._phase="error"}}_onCaptureEvent(e){switch(e.type){case"capture_listening":this._phase="listening";break;case"capture_received":this._stopCountdown(),this._result=e.result,e.duplicate_of?(this._duplicate=e.duplicate_of,this._phase="duplicate"):this._phase="captured";break;case"capture_timeout":this._stopCountdown(),this._phase="timeout";break;case"capture_error":this._stopCountdown(),this._error=e.error,this._phase="error";break;case"capture_cancelled":this._stopCountdown(),this._close()}}_startCountdown(){this._stopCountdown();const e=Date.now();this._countdown=window.setInterval(()=>{const t=(Date.now()-e)/1e3;this._timeRemaining=Math.max(0,Math.ceil(this.timeout-t)),this._timeRemaining<=0&&this._stopCountdown()},250)}_stopCountdown(){null!==this._countdown&&(clearInterval(this._countdown),this._countdown=null)}async _cancel(){if(this._sessionId)try{await this.api.cancelCapture(this._sessionId)}catch{}this._close()}async _testCommand(){if(!this._sessionId)return;const e=`__hair_test_${Date.now()}`;try{const t=await this.api.saveCapturedCommand({device_id:this.device.id,session_id:this._sessionId,command_name:e});await this.api.sendCommand(this.device.id,t.id),await this.api.deleteCommand(this.device.id,t.id)}catch(e){this._error=e.message,this._phase="error"}}async _save(e){if(this._sessionId)try{await this.api.saveCapturedCommand({device_id:this.device.id,session_id:this._sessionId,command_name:this.commandName}),this.dispatchEvent(new CustomEvent("command-saved",{detail:{saveAndNext:e,commandName:this.commandName},bubbles:!0,composed:!0})),this._close()}catch(e){this._error=e.message,this._phase="error"}}async _recapture(){this._unsubscribe&&(await this._unsubscribe(),this._unsubscribe=null),await this._beginCapture()}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_renderListening(){return B`
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
        `}_renderCaptured(){const e=this._result;return B`
            <div class="phase captured" aria-live="polite">
                <div class="check" aria-hidden="true">✓</div>
                <div class="title">Signal Captured!</div>
                <div class="meta">
                    Protocol: ${e.protocol??"Raw"}${e.code?B` · <code>${e.code}</code>`:""}
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
        `}_renderTimeout(){return B`
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
        `}_renderDuplicate(){const e=this._result;return B`
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
        `}_renderError(){return B`
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
        `}render(){return B`
            <ha-dialog
                open
                heading=${`Learning: "${this.commandName}"`}
                @closed=${this._cancel}
            >
                ${"listening"===this._phase?this._renderListening():"captured"===this._phase?this._renderCaptured():"timeout"===this._phase?this._renderTimeout():"duplicate"===this._phase?this._renderDuplicate():this._renderError()}
            </ha-dialog>
        `}};$e.styles=n`
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
    `,e([pe({attribute:!1})],$e.prototype,"api",void 0),e([pe({attribute:!1})],$e.prototype,"hass",void 0),e([pe({attribute:!1})],$e.prototype,"device",void 0),e([pe({attribute:!1})],$e.prototype,"commandName",void 0),e([pe({attribute:!1})],$e.prototype,"timeout",void 0),e([ue()],$e.prototype,"_phase",void 0),e([ue()],$e.prototype,"_result",void 0),e([ue()],$e.prototype,"_duplicate",void 0),e([ue()],$e.prototype,"_error",void 0),e([ue()],$e.prototype,"_timeRemaining",void 0),e([ue()],$e.prototype,"_sessionId",void 0),$e=e([de("ir-capture-dialog")],$e);let fe=class extends re{constructor(){super(...arguments),this._templates=[],this._busy=!1,this._captureName=null,this._captureQueue=[],this._customDialogOpen=!1,this._customName="",this._toast=null,this._confirmDelete=!1}connectedCallback(){super.connectedCallback(),this._loadTemplates()}updated(e){e.has("device")&&this.device&&this._loadTemplates()}async _loadTemplates(){try{this._templates=await this.api.listTemplates(this.device.device_type)}catch(e){this._templates=[]}}get _entries(){const e=new Map(this.device.commands.map(e=>[e.name.toLowerCase(),e])),t=new Set,i=[];for(const s of this._templates)t.add(s.name.toLowerCase()),i.push({template:s,name:s.name,command:e.get(s.name.toLowerCase())??null,essential:s.essential,custom:!1});for(const e of this.device.commands)t.has(e.name.toLowerCase())||i.push({template:null,name:e.name,command:e,essential:!1,custom:!0});return i}async _refresh(){this.device=await this.api.getDevice(this.device.id),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}_flash(e){this._toast=e,setTimeout(()=>{this._toast=null},2400)}async _onLearn(e){const{templateName:t}=e.detail;this._captureQueue=[],this._captureName=t}async _onRelearn(e){const{templateName:t}=e.detail;this._captureQueue=[],this._captureName=t}async _onTest(e){const{command:t}=e.detail;if(t){this._busy=!0;try{await this.api.sendCommand(this.device.id,t.id),this._flash(`Sent "${t.name}"`)}catch(e){this._flash(`Send failed: ${e.message}`)}finally{this._busy=!1}}}async _onDelete(e){const{command:t}=e.detail;if(t){this._busy=!0;try{await this.api.deleteCommand(this.device.id,t.id),await this._refresh(),this._flash(`Removed "${t.name}"`)}catch(e){this._flash(`Delete failed: ${e.message}`)}finally{this._busy=!1}}}_onCaptureClosed(){this._captureName=null,this._captureQueue=[]}async _onCommandSaved(e){const{saveAndNext:t,commandName:i}=e.detail;if(await this._refresh(),this._flash(`Saved "${i}"`),t){const e=this._buildNextQueue(i);if(e.length>0)return this._captureQueue=e,void(this._captureName=e[0])}this._captureName=null}_buildNextQueue(e){const t=new Set(this.device.commands.map(e=>e.name.toLowerCase()));return t.add(e.toLowerCase()),this._templates.filter(e=>e.essential&&!t.has(e.name.toLowerCase())).map(e=>e.name)}_openCustomDialog(){this._customName="",this._customDialogOpen=!0}_closeCustomDialog(){this._customDialogOpen=!1}_confirmCustom(){const e=this._customName.trim();e&&(this._customDialogOpen=!1,this._captureName=e,this._captureQueue=[])}async _deleteDevice(){this._busy=!0;try{await this.api.deleteDevice(this.device.id),this.dispatchEvent(new CustomEvent("device-deleted",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Delete failed: ${e.message}`)}finally{this._busy=!1,this._confirmDelete=!1}}render(){const e=this._entries,t=e.filter(e=>e.essential),i=e.filter(e=>!e.essential&&!e.custom),s=e.filter(e=>e.custom),a=e.filter(e=>null!==e.command).length,o=e.length||t.length,n=Object.keys(this.device.entity_config.command_mapping),r=this.device.entity_config.platform;return B`
            <section class="header">
                <div>
                    <h1>${this.device.name}</h1>
                    <div class="subtitle">
                        ${[this.device.manufacturer,this.device.model,this.device.emitter_entity_id].filter(Boolean).join(" • ")}
                    </div>
                </div>
                <div class="header-actions">
                    <mwc-button
                        @click=${()=>this._confirmDelete=!0}
                        ?disabled=${this._busy}
                    >
                        Delete
                    </mwc-button>
                </div>
            </section>

            <ir-progress-bar
                .learned=${a}
                .total=${o}
            ></ir-progress-bar>

            ${t.length>0?B`
                      <ha-card>
                          <h2>Essential Commands</h2>
                          ${t.map(e=>B`
                                  <ir-command-row
                                      .templateName=${e.name}
                                      .command=${e.command}
                                      .busy=${this._busy}
                                      @learn=${this._onLearn}
                                      @relearn=${this._onRelearn}
                                      @test=${this._onTest}
                                      @delete=${this._onDelete}
                                  ></ir-command-row>
                              `)}
                      </ha-card>
                  `:""}
            ${i.length>0?B`
                      <ha-card>
                          <h2>Optional Commands</h2>
                          ${i.map(e=>B`
                                  <ir-command-row
                                      .templateName=${e.name}
                                      .command=${e.command}
                                      .busy=${this._busy}
                                      @learn=${this._onLearn}
                                      @relearn=${this._onRelearn}
                                      @test=${this._onTest}
                                      @delete=${this._onDelete}
                                  ></ir-command-row>
                              `)}
                      </ha-card>
                  `:""}
            ${s.length>0?B`
                      <ha-card>
                          <h2>Custom Commands</h2>
                          ${s.map(e=>B`
                                  <ir-command-row
                                      .templateName=${e.name}
                                      .command=${e.command}
                                      .busy=${this._busy}
                                      @relearn=${this._onRelearn}
                                      @test=${this._onTest}
                                      @delete=${this._onDelete}
                                  ></ir-command-row>
                              `)}
                      </ha-card>
                  `:""}

            <div class="custom-add">
                <mwc-button
                    raised
                    @click=${this._openCustomDialog}
                    ?disabled=${this._busy}
                >
                    + Add Custom Command
                </mwc-button>
            </div>

            <ha-card class="entity-summary">
                <h2>Entity</h2>
                <div class="meta">
                    Platform: <code>${r}</code>
                </div>
                <div class="meta">
                    Mapped features:
                    ${n.length>0?n.join(", "):"None yet — capture commands to enable features."}
                </div>
            </ha-card>

            ${this._captureName?B`
                      <ir-capture-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .device=${this.device}
                          .commandName=${this._captureName}
                          @closed=${this._onCaptureClosed}
                          @command-saved=${this._onCommandSaved}
                      ></ir-capture-dialog>
                  `:""}
            ${this._customDialogOpen?B`
                      <ha-dialog
                          open
                          heading="Add Custom Command"
                          @closed=${this._closeCustomDialog}
                      >
                          <ha-textfield
                              label="Command name"
                              .value=${this._customName}
                              @input=${e=>this._customName=e.target.value}
                          ></ha-textfield>
                          <mwc-button slot="secondaryAction" @click=${this._closeCustomDialog}>
                              Cancel
                          </mwc-button>
                          <mwc-button slot="primaryAction" raised @click=${this._confirmCustom}>
                              Start Learning
                          </mwc-button>
                      </ha-dialog>
                  `:""}
            ${this._confirmDelete?B`
                      <ha-dialog
                          open
                          heading="Delete ${this.device.name}?"
                          @closed=${()=>this._confirmDelete=!1}
                      >
                          <p>
                              This removes all captured commands and the
                              auto-created entity. The action cannot be
                              undone.
                          </p>
                          <mwc-button
                              slot="secondaryAction"
                              @click=${()=>this._confirmDelete=!1}
                          >
                              Cancel
                          </mwc-button>
                          <mwc-button
                              slot="primaryAction"
                              class="destructive"
                              @click=${this._deleteDevice}
                          >
                              Delete
                          </mwc-button>
                      </ha-dialog>
                  `:""}
            ${this._toast?B`<div class="toast" role="status">${this._toast}</div>`:""}
        `}};fe.styles=n`
        :host {
            display: block;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
        }
        h1 {
            font-size: 1.5rem;
            margin: 0;
        }
        .subtitle {
            color: var(--secondary-text-color);
            margin-top: 4px;
            font-size: 0.9rem;
        }
        .header-actions {
            display: flex;
            gap: 6px;
        }
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
        .custom-add {
            margin: 16px 0;
        }
        .entity-summary .meta {
            font-size: 0.9rem;
            color: var(--primary-text-color);
            margin: 4px 0;
        }
        .destructive {
            --mdc-theme-primary: var(--error-color, #c62828);
        }
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
    `,e([pe({attribute:!1})],fe.prototype,"api",void 0),e([pe({attribute:!1})],fe.prototype,"hass",void 0),e([pe({attribute:!1})],fe.prototype,"device",void 0),e([ue()],fe.prototype,"_templates",void 0),e([ue()],fe.prototype,"_busy",void 0),e([ue()],fe.prototype,"_captureName",void 0),e([ue()],fe.prototype,"_captureQueue",void 0),e([ue()],fe.prototype,"_customDialogOpen",void 0),e([ue()],fe.prototype,"_customName",void 0),e([ue()],fe.prototype,"_toast",void 0),e([ue()],fe.prototype,"_confirmDelete",void 0),fe=e([de("ir-device-detail")],fe);const we=[{value:"tv",label:"TV / Monitor"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"soundbar",label:"Soundbar / Audio"},{value:"projector",label:"Projector"},{value:"other",label:"Other"}];let xe=class extends re{constructor(){super(...arguments),this._name="",this._manufacturer="",this._model="",this._deviceType="tv",this._emitterId="",this._captureProviderId=null,this._captureProviders=[],this._emitters=[],this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this._loadEmitters(),this._loadCaptureProviders()}_loadEmitters(){const e=this.hass?.states??{},t=[];for(const[i,s]of Object.entries(e))i.startsWith("infrared.")&&t.push({entity_id:i,name:s.attributes.friendly_name??i});this._emitters=t,1===t.length&&(this._emitterId=t[0].entity_id)}async _loadCaptureProviders(){try{this._captureProviders=await this.api.listCaptureProviders(),1===this._captureProviders.length&&(this._captureProviderId=this._captureProviders[0].device_id)}catch(e){this._error=`Could not load capture providers: ${e.message}`}}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _create(){if(this._name.trim())if(this._emitterId){this._busy=!0,this._error=null;try{const e=this._captureProviders.find(e=>e.device_id===this._captureProviderId),t=await this.api.createDevice({name:this._name.trim(),device_type:this._deviceType,emitter_entity_id:this._emitterId,manufacturer:this._manufacturer.trim()||null,model:this._model.trim()||null,capture_device_id:this._captureProviderId,capture_provider_type:e?.type??"esphome"});this.dispatchEvent(new CustomEvent("device-created",{detail:t,bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error="Pick an IR emitter.";else this._error="Name is required."}render(){return B`
            <ha-dialog
                open
                heading="Add IR Device"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <div class="field">
                    <label>Device type</label>
                    <select
                        .value=${this._deviceType}
                        @change=${e=>this._deviceType=e.target.value}
                    >
                        ${we.map(e=>B`
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

                <div class="field">
                    <label>IR emitter (sends commands)</label>
                    ${0===this._emitters.length?B`<ha-alert alert-type="warning">
                              No IR emitters found. Set up an ESPHome
                              <code>remote_transmitter</code> or a Broadlink
                              device first.
                          </ha-alert>`:B`
                              <select
                                  .value=${this._emitterId}
                                  @change=${e=>this._emitterId=e.target.value}
                              >
                                  <option value="" disabled>
                                      Select emitter…
                                  </option>
                                  ${this._emitters.map(e=>B`
                                          <option
                                              value=${e.entity_id}
                                              ?selected=${this._emitterId===e.entity_id}
                                          >
                                              ${e.name}
                                          </option>
                                      `)}
                              </select>
                          `}
                </div>

                <div class="field">
                    <label>IR receiver (learns commands)</label>
                    ${0===this._captureProviders.length?B`<ha-alert alert-type="info">
                              No capture-capable devices detected. You can
                              still create the device and add commands by
                              importing them later.
                          </ha-alert>`:B`
                              <select
                                  .value=${this._captureProviderId??""}
                                  @change=${e=>this._captureProviderId=e.target.value||null}
                              >
                                  <option value="">None (no learning)</option>
                                  ${this._captureProviders.map(e=>B`
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
        `}};function Ce(e){try{return new Date(e).toLocaleString(void 0,{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return e}}function Ae(e){try{const t=Date.now()-new Date(e).getTime();return t<6e4?"just now":t<36e5?`${Math.floor(t/6e4)} min ago`:t<864e5?`${Math.floor(t/36e5)}h ago`:`${Math.floor(t/864e5)}d ago`}catch{return""}}xe.styles=n`
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
    `,e([pe({attribute:!1})],xe.prototype,"api",void 0),e([pe({attribute:!1})],xe.prototype,"hass",void 0),e([ue()],xe.prototype,"_name",void 0),e([ue()],xe.prototype,"_manufacturer",void 0),e([ue()],xe.prototype,"_model",void 0),e([ue()],xe.prototype,"_deviceType",void 0),e([ue()],xe.prototype,"_emitterId",void 0),e([ue()],xe.prototype,"_captureProviderId",void 0),e([ue()],xe.prototype,"_captureProviders",void 0),e([ue()],xe.prototype,"_emitters",void 0),e([ue()],xe.prototype,"_busy",void 0),e([ue()],xe.prototype,"_error",void 0),xe=e([de("ir-add-device-dialog")],xe);const De="M4.93,4.93C3.12,6.74 2,9.24 2,12C2,14.76 3.12,17.26 4.93,19.07L6.34,17.66C4.89,16.22 4,14.22 4,12C4,9.79 4.89,7.78 6.34,6.34L4.93,4.93M19.07,4.93L17.66,6.34C19.11,7.78 20,9.79 20,12C20,14.22 19.11,16.22 17.66,17.66L19.07,19.07C20.88,17.26 22,14.76 22,12C22,9.24 20.88,6.74 19.07,4.93M7.76,7.76C6.67,8.85 6,10.35 6,12C6,13.65 6.67,15.15 7.76,16.24L9.17,14.83C8.45,14.11 8,13.11 8,12C8,10.89 8.45,9.89 9.17,9.17L7.76,7.76M16.24,7.76L14.83,9.17C15.55,9.89 16,10.89 16,12C16,13.11 15.55,14.11 14.83,14.83L16.24,16.24C17.33,15.15 18,13.65 18,12C18,10.35 17.33,8.85 16.24,7.76M12,10A2,2 0 0,0 10,12A2,2 0 0,0 12,14A2,2 0 0,0 14,12A2,2 0 0,0 12,10Z",ke="M2,5.27L3.28,4L20,20.72L18.73,22L15.65,18.92C14.5,19.3 13.28,19.5 12,19.5C7,19.5 2.73,16.39 1,12C1.69,10.24 2.79,8.69 4.19,7.46L2,5.27M12,9A3,3 0 0,1 15,12C15,12.35 14.94,12.69 14.83,13L11,9.17C11.31,9.06 11.65,9 12,9M12,4.5C17,4.5 21.27,7.61 23,12C22.18,14.08 20.79,15.88 19,17.19L17.58,15.76C18.94,14.82 20.06,13.54 20.82,12C19.17,8.64 15.76,6.5 12,6.5C10.91,6.5 9.84,6.68 8.84,7L7.3,5.47C8.74,4.85 10.33,4.5 12,4.5M3.18,12C4.83,15.36 8.24,17.5 12,17.5C12.69,17.5 13.37,17.43 14,17.29L11.72,15C10.29,14.85 9.15,13.71 9,12.28L5.6,8.87C4.61,9.72 3.78,10.78 3.18,12Z",Ee="M12,9A3,3 0 0,1 15,12A3,3 0 0,1 12,15A3,3 0 0,1 9,12A3,3 0 0,1 12,9M12,4.5C17,4.5 21.27,7.61 23,12C21.27,16.39 17,19.5 12,19.5C7,19.5 2.73,16.39 1,12C2.73,7.61 7,4.5 12,4.5M3.18,12C4.83,15.36 8.24,17.5 12,17.5C15.76,17.5 19.17,15.36 20.82,12C19.17,8.64 15.76,6.5 12,6.5C8.24,6.5 4.83,8.64 3.18,12Z";let Se=class extends re{constructor(){super(...arguments),this._devices=[],this._loading=!0,this._error=null,this._showDismissed=!1,this._expandedId=null,this._expandedDevice=null,this._flashIds=new Set,this._unsubLive=null}connectedCallback(){super.connectedCallback(),this._load(),this._subscribeLive()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeLive()}async _load(){this._loading=!0;try{this._devices=await this.api.getUnknownDevices({include_dismissed:this._showDismissed}),this._error=null}catch(e){this._error=`Failed to load: ${e.message}`}finally{this._loading=!1}}async _subscribeLive(){try{this._unsubLive=await this.api.subscribeUnknownSignals(e=>{this._onLiveSignal(e)})}catch{}}async _unsubscribeLive(){this._unsubLive&&(await this._unsubLive(),this._unsubLive=null)}_onLiveSignal(e){const t=this._devices.findIndex(t=>t.id===e.device_id);if(t>=0){{const i={...this._devices[t]};i.hit_count=e.hit_count,i.last_seen=(new Date).toISOString();const s=[...this._devices];s[t]=i,this._devices=s}this._flashIds=new Set([...this._flashIds,e.device_id]),setTimeout(()=>{const t=new Set(this._flashIds);t.delete(e.device_id),this._flashIds=t},800)}else this._load()}async _toggleExpand(e){if(this._expandedId===e)return this._expandedId=null,void(this._expandedDevice=null);this._expandedId=e;try{this._expandedDevice=await this.api.getUnknownDevice(e)}catch{this._expandedDevice=null}}async _dismiss(e){try{await this.api.dismissUnknown(e),await this._load(),this._expandedId===e&&(this._expandedId=null,this._expandedDevice=null)}catch(e){this._error=`Dismiss failed: ${e.message}`}}async _undismiss(e){try{await this.api.undismissUnknown(e),await this._load()}catch(e){this._error=`Restore failed: ${e.message}`}}async _clearAll(){try{await this.api.clearUnknowns(),this._devices=[],this._expandedId=null,this._expandedDevice=null}catch(e){this._error=`Clear failed: ${e.message}`}}_toggleDismissed(){this._showDismissed=!this._showDismissed,this._load()}render(){return B`
            <div class="toolbar">
                <span class="title">
                    <ha-svg-icon .path=${De}></ha-svg-icon>
                    Unknown Signals
                    ${this._loading?"":B`<span class="count">(${this._devices.length})</span>`}
                </span>
                <div class="toolbar-actions">
                    <mwc-button
                        dense
                        @click=${this._toggleDismissed}
                    >
                        <ha-svg-icon
                            .path=${this._showDismissed?ke:Ee}
                            slot="icon"
                        ></ha-svg-icon>
                        ${this._showDismissed?"Hide Dismissed":"Show Dismissed"}
                    </mwc-button>
                    ${this._devices.length>0?B`
                              <mwc-button
                                  dense
                                  @click=${this._clearAll}
                              >
                                  <ha-svg-icon
                                      .path=${"M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19M8,9H16V19H8V9M15.5,4L14.5,3H9.5L8.5,4H5V6H19V4H15.5Z"}
                                      slot="icon"
                                  ></ha-svg-icon>
                                  Clear All
                              </mwc-button>
                          `:""}
                </div>
            </div>

            ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

            ${this._loading?B`<div class="loading">Scanning for signals...</div>`:0===this._devices.length?B`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${De}></ha-svg-icon>
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
                    `:B`
                        <div class="device-list">
                            ${this._devices.map(e=>this._renderDevice(e))}
                        </div>
                    `}
        `}_renderDevice(e){const t=this._expandedId===e.id,i=this._flashIds.has(e.id);return B`
            <ha-card class="device ${i?"flash":""} ${e.dismissed?"dismissed":""}">
                <div
                    class="device-row"
                    @click=${()=>this._toggleExpand(e.id)}
                >
                    <div class="device-info">
                        <div class="device-header">
                            <span class="protocol">${e.protocol??"RAW"}</span>
                            ${e.device_address?B`<span class="address">addr: ${e.device_address}</span>`:""}
                            ${e.dismissed?B`<span class="dismissed-badge">dismissed</span>`:""}
                        </div>
                        <div class="device-stats">
                            <span class="stat">
                                <strong>${e.hit_count}</strong> hits
                            </span>
                            <span class="stat">
                                <strong>${e.signal_count}</strong> signals
                            </span>
                            <span class="stat last-seen" title=${Ce(e.last_seen)}>
                                ${Ae(e.last_seen)}
                            </span>
                        </div>
                    </div>
                    <ha-svg-icon
                        class="expand-icon"
                        .path=${t?"M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z":"M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z"}
                    ></ha-svg-icon>
                </div>

                ${t&&this._expandedDevice?this._renderExpanded(this._expandedDevice,e.dismissed):""}
            </ha-card>
        `}_renderExpanded(e,t){return B`
            <div class="expanded">
                <div class="signal-header">
                    <span>Signals (${e.signals.length})</span>
                    <span class="first-seen">First seen: ${Ce(e.first_seen)}</span>
                </div>
                <div class="signal-list">
                    ${e.signals.map(e=>B`
                            <div class="signal-row">
                                <div class="signal-info">
                                    <code class="signal-code"
                                        >${e.protocol??"RAW"}: ${e.code??`${e.raw_timings.length} timings`}</code
                                    >
                                </div>
                                <div class="signal-meta">
                                    <span>${e.hit_count} hits</span>
                                    <span title=${Ce(e.last_seen)}
                                        >${Ae(e.last_seen)}</span
                                    >
                                </div>
                            </div>
                        `)}
                </div>
                <div class="expanded-actions">
                    ${t?B`
                              <mwc-button
                                  dense
                                  @click=${()=>this._undismiss(e.id)}
                              >
                                  <ha-svg-icon .path=${Ee} slot="icon"></ha-svg-icon>
                                  Restore
                              </mwc-button>
                          `:B`
                              <mwc-button
                                  dense
                                  @click=${()=>this._dismiss(e.id)}
                              >
                                  <ha-svg-icon .path=${ke} slot="icon"></ha-svg-icon>
                                  Dismiss
                              </mwc-button>
                          `}
                </div>
            </div>
        `}};Se.styles=n`
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
        .toolbar-actions mwc-button {
            --mdc-typography-button-font-size: 0.8rem;
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
            justify-content: space-between;
            align-items: center;
            padding: 6px 8px;
            background: var(--secondary-background-color);
            border-radius: 4px;
            gap: 12px;
        }
        .signal-code {
            font-size: 0.82rem;
            word-break: break-all;
        }
        .signal-meta {
            display: flex;
            gap: 12px;
            font-size: 0.8rem;
            color: var(--secondary-text-color);
            white-space: nowrap;
        }

        .expanded-actions {
            margin-top: 12px;
            display: flex;
            gap: 8px;
            justify-content: flex-end;
        }
    `,e([pe({attribute:!1})],Se.prototype,"api",void 0),e([pe({attribute:!1})],Se.prototype,"hass",void 0),e([ue()],Se.prototype,"_devices",void 0),e([ue()],Se.prototype,"_loading",void 0),e([ue()],Se.prototype,"_error",void 0),e([ue()],Se.prototype,"_showDismissed",void 0),e([ue()],Se.prototype,"_expandedId",void 0),e([ue()],Se.prototype,"_expandedDevice",void 0),e([ue()],Se.prototype,"_flashIds",void 0),Se=e([de("ir-signal-monitor")],Se);let Me=class extends re{constructor(){super(...arguments),this.narrow=!1,this._activeTab="devices",this._devices=[],this._selectedDevice=null,this._loading=!0,this._error=null,this._addDialogOpen=!1,this._api=null}connectedCallback(){super.connectedCallback(),this.hass&&this._init()}updated(e){e.has("hass")&&this.hass&&!this._api&&this._init()}_init(){this._api=new me(this.hass),this._refreshDevices()}async _refreshDevices(){if(this._api){this._loading=!0;try{this._devices=await this._api.listDevices(),this._error=null}catch(e){this._error=`Failed to load devices: ${e.message}`}finally{this._loading=!1}}}async _openDevice(e){if(this._api)try{this._selectedDevice=await this._api.getDevice(e);const t=`${this.route?.prefix??"/ir-devices"}/${e}`;history.pushState({deviceId:e},"",t)}catch(e){this._error=`Failed to open device: ${e.message}`}}_backToList(){this._selectedDevice=null,history.pushState({},"",this.route?.prefix??"/ir-devices")}_openAddDialog(){this._addDialogOpen=!0}_closeAddDialog(){this._addDialogOpen=!1}async _onDeviceCreated(e){this._addDialogOpen=!1,await this._refreshDevices(),this._selectedDevice=e.detail}async _onDeviceChanged(){await this._refreshDevices(),this._selectedDevice&&this._api&&(this._selectedDevice=await this._api.getDevice(this._selectedDevice.id))}async _onDeviceDeleted(){this._selectedDevice=null,await this._refreshDevices()}_switchTab(e){this._selectedDevice&&this._backToList(),this._activeTab=e}render(){if(!this._api)return B`<div class="loading">Loading…</div>`;const e=!this._selectedDevice;return B`
            <ha-top-app-bar-fixed>
                <ha-icon-button
                    slot="navigationIcon"
                    .path=${this._selectedDevice?"M19,11H7.83L12.83,6L11.41,4.59L4,12L11.41,19.41L12.83,18L7.83,13H19V11Z":"M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z"}
                    @click=${this._selectedDevice?this._backToList:void 0}
                ></ha-icon-button>
                <span slot="title">
                    ${this._selectedDevice?this._selectedDevice.name:"IR Devices"}
                </span>
            </ha-top-app-bar-fixed>

            ${e?B`
                      <div class="tab-bar">
                          <button
                              class="tab ${"devices"===this._activeTab?"active":""}"
                              @click=${()=>this._switchTab("devices")}
                          >
                              Devices
                          </button>
                          <button
                              class="tab ${"monitor"===this._activeTab?"active":""}"
                              @click=${()=>this._switchTab("monitor")}
                          >
                              Signal Monitor
                          </button>
                      </div>
                  `:""}

            <div class="content">
                ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}
                ${this._selectedDevice?B`
                          <ir-device-detail
                              .api=${this._api}
                              .device=${this._selectedDevice}
                              .hass=${this.hass}
                              @device-changed=${this._onDeviceChanged}
                              @device-deleted=${this._onDeviceDeleted}
                          ></ir-device-detail>
                      `:"devices"===this._activeTab?B`
                            <ir-device-list
                                .devices=${this._devices}
                                .loading=${this._loading}
                                @device-selected=${e=>this._openDevice(e.detail)}
                                @add-device=${this._openAddDialog}
                            ></ir-device-list>

                            ${!this._loading&&this._devices.length>0?B`
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
                        `:B`
                            <ir-signal-monitor
                                .api=${this._api}
                                .hass=${this.hass}
                            ></ir-signal-monitor>
                        `}
            </div>

            ${this._addDialogOpen?B`
                      <ir-add-device-dialog
                          .api=${this._api}
                          .hass=${this.hass}
                          @closed=${this._closeAddDialog}
                          @device-created=${this._onDeviceCreated}
                      ></ir-add-device-dialog>
                  `:""}
        `}};Me.styles=n`
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
    `,e([pe({attribute:!1})],Me.prototype,"hass",void 0),e([pe({attribute:!1})],Me.prototype,"narrow",void 0),e([pe({attribute:!1})],Me.prototype,"route",void 0),e([pe({attribute:!1})],Me.prototype,"panel",void 0),e([ue()],Me.prototype,"_activeTab",void 0),e([ue()],Me.prototype,"_devices",void 0),e([ue()],Me.prototype,"_selectedDevice",void 0),e([ue()],Me.prototype,"_loading",void 0),e([ue()],Me.prototype,"_error",void 0),e([ue()],Me.prototype,"_addDialogOpen",void 0),Me=e([de("ha-panel-ir-devices")],Me);export{Me as HaPanelIrDevices};
