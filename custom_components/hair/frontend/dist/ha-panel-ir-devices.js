function e(e,t,i,o){var s,r=arguments.length,a=r<3?t:null===o?o=Object.getOwnPropertyDescriptor(t,i):o;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)a=Reflect.decorate(e,t,i,o);else for(var n=e.length-1;n>=0;n--)(s=e[n])&&(a=(r<3?s(a):r>3?s(t,i,a):s(t,i))||a);return r>3&&a&&Object.defineProperty(t,i,a),a}"function"==typeof SuppressedError&&SuppressedError;const t=globalThis,i=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,o=Symbol(),s=new WeakMap;let r=class{constructor(e,t,i){if(this._$cssResult$=!0,i!==o)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(i&&void 0===e){const i=void 0!==t&&1===t.length;i&&(e=s.get(t)),void 0===e&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),i&&s.set(t,e))}return e}toString(){return this.cssText}};const a=(e,...t)=>{const i=1===e.length?e[0]:t.reduce((t,i,o)=>t+(e=>{if(!0===e._$cssResult$)return e.cssText;if("number"==typeof e)return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+e[o+1],e[0]);return new r(i,e,o)},n=i?e=>e:e=>e instanceof CSSStyleSheet?(e=>{let t="";for(const i of e.cssRules)t+=i.cssText;return(e=>new r("string"==typeof e?e:e+"",void 0,o))(t)})(e):e,{is:l,defineProperty:d,getOwnPropertyDescriptor:c,getOwnPropertyNames:h,getOwnPropertySymbols:p,getPrototypeOf:g}=Object,u=globalThis,m=u.trustedTypes,v=m?m.emptyScript:"",_=u.reactiveElementPolyfillSupport,b=(e,t)=>e,f={toAttribute(e,t){switch(t){case Boolean:e=e?v:null;break;case Object:case Array:e=null==e?e:JSON.stringify(e)}return e},fromAttribute(e,t){let i=e;switch(t){case Boolean:i=null!==e;break;case Number:i=null===e?null:Number(e);break;case Object:case Array:try{i=JSON.parse(e)}catch(e){i=null}}return i}},y=(e,t)=>!l(e,t),x={attribute:!0,type:String,converter:f,reflect:!1,useDefault:!1,hasChanged:y};Symbol.metadata??=Symbol("metadata"),u.litPropertyMetadata??=new WeakMap;let w=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=x){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const i=Symbol(),o=this.getPropertyDescriptor(e,i,t);void 0!==o&&d(this.prototype,e,o)}}static getPropertyDescriptor(e,t,i){const{get:o,set:s}=c(this.prototype,e)??{get(){return this[t]},set(e){this[t]=e}};return{get:o,set(t){const r=o?.call(this);s?.call(this,t),this.requestUpdate(e,r,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??x}static _$Ei(){if(this.hasOwnProperty(b("elementProperties")))return;const e=g(this);e.finalize(),void 0!==e.l&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(b("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(b("properties"))){const e=this.properties,t=[...h(e),...p(e)];for(const i of t)this.createProperty(i,e[i])}const e=this[Symbol.metadata];if(null!==e){const t=litPropertyMetadata.get(e);if(void 0!==t)for(const[e,i]of t)this.elementProperties.set(e,i)}this._$Eh=new Map;for(const[e,t]of this.elementProperties){const i=this._$Eu(e,t);void 0!==i&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const i=new Set(e.flat(1/0).reverse());for(const e of i)t.unshift(n(e))}else void 0!==e&&t.push(n(e));return t}static _$Eu(e,t){const i=t.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof e?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),void 0!==this.renderRoot&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const i of t.keys())this.hasOwnProperty(i)&&(e.set(i,this[i]),delete this[i]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((e,o)=>{if(i)e.adoptedStyleSheets=o.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(const i of o){const o=document.createElement("style"),s=t.litNonce;void 0!==s&&o.setAttribute("nonce",s),o.textContent=i.cssText,e.appendChild(o)}})(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,i){this._$AK(e,i)}_$ET(e,t){const i=this.constructor.elementProperties.get(e),o=this.constructor._$Eu(e,i);if(void 0!==o&&!0===i.reflect){const s=(void 0!==i.converter?.toAttribute?i.converter:f).toAttribute(t,i.type);this._$Em=e,null==s?this.removeAttribute(o):this.setAttribute(o,s),this._$Em=null}}_$AK(e,t){const i=this.constructor,o=i._$Eh.get(e);if(void 0!==o&&this._$Em!==o){const e=i.getPropertyOptions(o),s="function"==typeof e.converter?{fromAttribute:e.converter}:void 0!==e.converter?.fromAttribute?e.converter:f;this._$Em=o;const r=s.fromAttribute(t,e.type);this[o]=r??this._$Ej?.get(o)??r,this._$Em=null}}requestUpdate(e,t,i,o=!1,s){if(void 0!==e){const r=this.constructor;if(!1===o&&(s=this[e]),i??=r.getPropertyOptions(e),!((i.hasChanged??y)(s,t)||i.useDefault&&i.reflect&&s===this._$Ej?.get(e)&&!this.hasAttribute(r._$Eu(e,i))))return;this.C(e,t,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(e,t,{useDefault:i,reflect:o,wrapped:s},r){i&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,r??t??this[e]),!0!==s||void 0!==r)||(this._$AL.has(e)||(this.hasUpdated||i||(t=void 0),this._$AL.set(e,t)),!0===o&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}const e=this.scheduleUpdate();return null!=e&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[e,t]of this._$Ep)this[e]=t;this._$Ep=void 0}const e=this.constructor.elementProperties;if(e.size>0)for(const[t,i]of e){const{wrapped:e}=i,o=this[t];!0!==e||this._$AL.has(t)||void 0===o||this.C(t,void 0,i,o)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(e=>e.hostUpdate?.()),this.update(t)):this._$EM()}catch(t){throw e=!1,this._$EM(),t}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(e){}firstUpdated(e){}};w.elementStyles=[],w.shadowRootOptions={mode:"open"},w[b("elementProperties")]=new Map,w[b("finalized")]=new Map,_?.({ReactiveElement:w}),(u.reactiveElementVersions??=[]).push("2.1.2");const $=globalThis,D=e=>e,k=$.trustedTypes,C=k?k.createPolicy("lit-html",{createHTML:e=>e}):void 0,T="$lit$",E=`lit$${Math.random().toFixed(9).slice(2)}$`,A="?"+E,S=`<${A}>`,I=document,M=()=>I.createComment(""),N=e=>null===e||"object"!=typeof e&&"function"!=typeof e,P=Array.isArray,H="[ \t\n\f\r]",R=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,L=/-->/g,O=/>/g,z=RegExp(`>|${H}(?:([^\\s"'>=/]+)(${H}*=${H}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),V=/'/g,F=/"/g,U=/^(?:script|style|textarea|title)$/i,j=(e,...t)=>({_$litType$:1,strings:e,values:t}),B=Symbol.for("lit-noChange"),X=Symbol.for("lit-nothing"),q=new WeakMap,Y=I.createTreeWalker(I,129);function W(e,t){if(!P(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==C?C.createHTML(t):t}class Z{constructor({strings:e,_$litType$:t},i){let o;this.parts=[];let s=0,r=0;const a=e.length-1,n=this.parts,[l,d]=((e,t)=>{const i=e.length-1,o=[];let s,r=2===t?"<svg>":3===t?"<math>":"",a=R;for(let t=0;t<i;t++){const i=e[t];let n,l,d=-1,c=0;for(;c<i.length&&(a.lastIndex=c,l=a.exec(i),null!==l);)c=a.lastIndex,a===R?"!--"===l[1]?a=L:void 0!==l[1]?a=O:void 0!==l[2]?(U.test(l[2])&&(s=RegExp("</"+l[2],"g")),a=z):void 0!==l[3]&&(a=z):a===z?">"===l[0]?(a=s??R,d=-1):void 0===l[1]?d=-2:(d=a.lastIndex-l[2].length,n=l[1],a=void 0===l[3]?z:'"'===l[3]?F:V):a===F||a===V?a=z:a===L||a===O?a=R:(a=z,s=void 0);const h=a===z&&e[t+1].startsWith("/>")?" ":"";r+=a===R?i+S:d>=0?(o.push(n),i.slice(0,d)+T+i.slice(d)+E+h):i+E+(-2===d?t:h)}return[W(e,r+(e[i]||"<?>")+(2===t?"</svg>":3===t?"</math>":"")),o]})(e,t);if(this.el=Z.createElement(l,i),Y.currentNode=this.el.content,2===t||3===t){const e=this.el.content.firstChild;e.replaceWith(...e.childNodes)}for(;null!==(o=Y.nextNode())&&n.length<a;){if(1===o.nodeType){if(o.hasAttributes())for(const e of o.getAttributeNames())if(e.endsWith(T)){const t=d[r++],i=o.getAttribute(e).split(E),a=/([.?@])?(.*)/.exec(t);n.push({type:1,index:s,name:a[2],strings:i,ctor:"."===a[1]?ee:"?"===a[1]?te:"@"===a[1]?ie:Q}),o.removeAttribute(e)}else e.startsWith(E)&&(n.push({type:6,index:s}),o.removeAttribute(e));if(U.test(o.tagName)){const e=o.textContent.split(E),t=e.length-1;if(t>0){o.textContent=k?k.emptyScript:"";for(let i=0;i<t;i++)o.append(e[i],M()),Y.nextNode(),n.push({type:2,index:++s});o.append(e[t],M())}}}else if(8===o.nodeType)if(o.data===A)n.push({type:2,index:s});else{let e=-1;for(;-1!==(e=o.data.indexOf(E,e+1));)n.push({type:7,index:s}),e+=E.length-1}s++}}static createElement(e,t){const i=I.createElement("template");return i.innerHTML=e,i}}function K(e,t,i=e,o){if(t===B)return t;let s=void 0!==o?i._$Co?.[o]:i._$Cl;const r=N(t)?void 0:t._$litDirective$;return s?.constructor!==r&&(s?._$AO?.(!1),void 0===r?s=void 0:(s=new r(e),s._$AT(e,i,o)),void 0!==o?(i._$Co??=[])[o]=s:i._$Cl=s),void 0!==s&&(t=K(e,s._$AS(e,t.values),s,o)),t}class G{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:i}=this._$AD,o=(e?.creationScope??I).importNode(t,!0);Y.currentNode=o;let s=Y.nextNode(),r=0,a=0,n=i[0];for(;void 0!==n;){if(r===n.index){let t;2===n.type?t=new J(s,s.nextSibling,this,e):1===n.type?t=new n.ctor(s,n.name,n.strings,this,e):6===n.type&&(t=new oe(s,this,e)),this._$AV.push(t),n=i[++a]}r!==n?.index&&(s=Y.nextNode(),r++)}return Y.currentNode=I,o}p(e){let t=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(e,i,t),t+=i.strings.length-2):i._$AI(e[t])),t++}}class J{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,i,o){this.type=2,this._$AH=X,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=i,this.options=o,this._$Cv=o?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return void 0!==t&&11===e?.nodeType&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=K(this,e,t),N(e)?e===X||null==e||""===e?(this._$AH!==X&&this._$AR(),this._$AH=X):e!==this._$AH&&e!==B&&this._(e):void 0!==e._$litType$?this.$(e):void 0!==e.nodeType?this.T(e):(e=>P(e)||"function"==typeof e?.[Symbol.iterator])(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==X&&N(this._$AH)?this._$AA.nextSibling.data=e:this.T(I.createTextNode(e)),this._$AH=e}$(e){const{values:t,_$litType$:i}=e,o="number"==typeof i?this._$AC(e):(void 0===i.el&&(i.el=Z.createElement(W(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===o)this._$AH.p(t);else{const e=new G(o,this),i=e.u(this.options);e.p(t),this.T(i),this._$AH=e}}_$AC(e){let t=q.get(e.strings);return void 0===t&&q.set(e.strings,t=new Z(e)),t}k(e){P(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let i,o=0;for(const s of e)o===t.length?t.push(i=new J(this.O(M()),this.O(M()),this,this.options)):i=t[o],i._$AI(s),o++;o<t.length&&(this._$AR(i&&i._$AB.nextSibling,o),t.length=o)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){const t=D(e).nextSibling;D(e).remove(),e=t}}setConnected(e){void 0===this._$AM&&(this._$Cv=e,this._$AP?.(e))}}class Q{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,i,o,s){this.type=1,this._$AH=X,this._$AN=void 0,this.element=e,this.name=t,this._$AM=o,this.options=s,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=X}_$AI(e,t=this,i,o){const s=this.strings;let r=!1;if(void 0===s)e=K(this,e,t,0),r=!N(e)||e!==this._$AH&&e!==B,r&&(this._$AH=e);else{const o=e;let a,n;for(e=s[0],a=0;a<s.length-1;a++)n=K(this,o[i+a],t,a),n===B&&(n=this._$AH[a]),r||=!N(n)||n!==this._$AH[a],n===X?e=X:e!==X&&(e+=(n??"")+s[a+1]),this._$AH[a]=n}r&&!o&&this.j(e)}j(e){e===X?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class ee extends Q{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===X?void 0:e}}class te extends Q{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==X)}}class ie extends Q{constructor(e,t,i,o,s){super(e,t,i,o,s),this.type=5}_$AI(e,t=this){if((e=K(this,e,t,0)??X)===B)return;const i=this._$AH,o=e===X&&i!==X||e.capture!==i.capture||e.once!==i.once||e.passive!==i.passive,s=e!==X&&(i===X||o);o&&this.element.removeEventListener(this.name,this,i),s&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}}class oe{constructor(e,t,i){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(e){K(this,e)}}const se={I:J},re=$.litHtmlPolyfillSupport;re?.(Z,J),($.litHtmlVersions??=[]).push("3.3.3");const ae=globalThis;let ne=class extends w{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=((e,t,i)=>{const o=i?.renderBefore??t;let s=o._$litPart$;if(void 0===s){const e=i?.renderBefore??null;o._$litPart$=s=new J(t.insertBefore(M(),e),e,void 0,i??{})}return s._$AI(e),s})(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return B}};ne._$litElement$=!0,ne.finalized=!0,ae.litElementHydrateSupport?.({LitElement:ne});const le=ae.litElementPolyfillSupport;le?.({LitElement:ne}),(ae.litElementVersions??=[]).push("4.2.2");const de=e=>(t,i)=>{void 0!==i?i.addInitializer(()=>{customElements.define(e,t)}):customElements.define(e,t)},ce={attribute:!0,type:String,converter:f,reflect:!1,hasChanged:y},he=(e=ce,t,i)=>{const{kind:o,metadata:s}=i;let r=globalThis.litPropertyMetadata.get(s);if(void 0===r&&globalThis.litPropertyMetadata.set(s,r=new Map),"setter"===o&&((e=Object.create(e)).wrapped=!0),r.set(i.name,e),"accessor"===o){const{name:o}=i;return{set(i){const s=t.get.call(this);t.set.call(this,i),this.requestUpdate(o,s,e,!0,i)},init(t){return void 0!==t&&this.C(o,void 0,e,t),t}}}if("setter"===o){const{name:o}=i;return function(i){const s=this[o];t.call(this,i),this.requestUpdate(o,s,e,!0,i)}}throw Error("Unsupported decorator location: "+o)};function pe(e){return(t,i)=>"object"==typeof i?he(e,t,i):((e,t,i)=>{const o=t.hasOwnProperty(i);return t.constructor.createProperty(i,e),o?Object.getOwnPropertyDescriptor(t,i):void 0})(e,t,i)}function ge(e){return pe({...e,state:!0,attribute:!1})}class ue{constructor(e){this.hass=e}listDevices(){return this.hass.connection.sendMessagePromise({type:"hair/devices"})}getDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/device",device_id:e})}createDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/device/create",...e})}updateDevice(e,t){return this.hass.connection.sendMessagePromise({type:"hair/device/update",device_id:e,...t})}deleteDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/device/delete",device_id:e})}duplicateDevice(e,t){return this.hass.connection.sendMessagePromise({type:"hair/device/duplicate",device_id:e,new_name:t})}deleteCommand(e,t){return this.hass.connection.sendMessagePromise({type:"hair/command/delete",device_id:e,command_id:t})}reorderCommands(e,t){return this.hass.connection.sendMessagePromise({type:"hair/device/reorder-commands",device_id:e,command_ids:t})}sendCommand(e,t){return this.hass.connection.sendMessagePromise({type:"hair/command/send",device_id:e,command_id:t})}listTemplates(e){return this.hass.connection.sendMessagePromise({type:"hair/templates",device_type:e})}listCaptureProviders(){return this.hass.connection.sendMessagePromise({type:"hair/capture/providers"})}listReceivers(){return this.hass.connection.sendMessagePromise({type:"hair/receivers"})}async startCapture(e,t,i){let o=null;const s=await this.hass.connection.subscribeMessage(e=>{e.type?.startsWith("capture_")?i(e):e.session_id&&(o=e)},{type:"hair/capture/start",device_id:e,timeout:t});if(await Promise.resolve(),null===o)throw new Error("Capture session did not start");return{session:o,unsubscribe:s}}cancelCapture(e){return this.hass.connection.sendMessagePromise({type:"hair/capture/cancel",session_id:e})}saveCapturedCommand(e){return this.hass.connection.sendMessagePromise({type:"hair/capture/save",...e})}getActionOptions(e){return this.hass.connection.sendMessagePromise({type:"hair/device/action-options",device_type:e})}updateMapping(e,t,i){return this.hass.connection.sendMessagePromise({type:"hair/device/update-mapping",device_id:e,command_name:t,action_key:i})}getUnknownDevices(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/devices",...e})}getUnknownDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/device",device_id:e})}dismissUnknown(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/dismiss",device_id:e})}undismissUnknown(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/undismiss",device_id:e})}assignSignal(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/assign",...e})}assignToNewDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/assign-new-device",...e})}deleteSignal(e,t){return this.hass.connection.sendMessagePromise({type:"hair/unknown/signal/delete",device_id:e,signal_fingerprint:t})}testSignal(e,t){const i={type:"hair/unknown/test",signal_fingerprint:e};return t&&(i.emitter_entity_id=t),this.hass.connection.sendMessagePromise(i)}renameUnknown(e,t){return this.hass.connection.sendMessagePromise({type:"hair/unknown/rename",device_id:e,label:t})}clearUnknowns(){return this.hass.connection.sendMessagePromise({type:"hair/unknown/clear"})}async subscribeUnknownSignals(e){return this.hass.connection.subscribeEvents(t=>e(t.data),"hair_signal_detected")}async subscribeSignalRemoved(e){return this.hass.connection.subscribeEvents(t=>e(t.data),"hair_signal_removed")}listTriggers(){return this.hass.connection.sendMessagePromise({type:"hair/triggers"})}createTrigger(e){return this.hass.connection.sendMessagePromise({type:"hair/trigger/create",...e})}updateTrigger(e,t){return this.hass.connection.sendMessagePromise({type:"hair/trigger/update",trigger_id:e,...t})}deleteTrigger(e){return this.hass.connection.sendMessagePromise({type:"hair/trigger/delete",trigger_id:e})}async subscribeTriggerFired(e){return this.hass.connection.subscribeMessage(e,{type:"hair/trigger/subscribe"})}}const me=e=>(...t)=>({_$litDirective$:e,values:t});let ve=class{constructor(e){}get _$AU(){return this._$AM._$AU}_$AT(e,t,i){this._$Ct=e,this._$AM=t,this._$Ci=i}_$AS(e,t){return this.update(e,t)}update(e,t){return this.render(...t)}};const{I:_e}=se,be=e=>e,fe=()=>document.createComment(""),ye=(e,t,i)=>{const o=e._$AA.parentNode,s=void 0===t?e._$AB:t._$AA;if(void 0===i){const t=o.insertBefore(fe(),s),r=o.insertBefore(fe(),s);i=new _e(t,r,e,e.options)}else{const t=i._$AB.nextSibling,r=i._$AM,a=r!==e;if(a){let t;i._$AQ?.(e),i._$AM=e,void 0!==i._$AP&&(t=e._$AU)!==r._$AU&&i._$AP(t)}if(t!==s||a){let e=i._$AA;for(;e!==t;){const t=be(e).nextSibling;be(o).insertBefore(e,s),e=t}}}return i},xe=(e,t,i=e)=>(e._$AI(t,i),e),we={},$e=(e,t=we)=>e._$AH=t,De=e=>{e._$AR(),e._$AA.remove()},ke=me(class extends ve{constructor(){super(...arguments),this.key=X}render(e,t){return this.key=e,t}update(e,[t,i]){return t!==this.key&&($e(e),this.key=t),i}}),Ce=(e,t,i)=>{const o=new Map;for(let s=t;s<=i;s++)o.set(e[s],s);return o},Te=me(class extends ve{constructor(e){if(super(e),2!==e.type)throw Error("repeat() can only be used in text expressions")}dt(e,t,i){let o;void 0===i?i=t:void 0!==t&&(o=t);const s=[],r=[];let a=0;for(const t of e)s[a]=o?o(t,a):a,r[a]=i(t,a),a++;return{values:r,keys:s}}render(e,t,i){return this.dt(e,t,i).values}update(e,[t,i,o]){const s=(e=>e._$AH)(e),{values:r,keys:a}=this.dt(t,i,o);if(!Array.isArray(s))return this.ut=a,r;const n=this.ut??=[],l=[];let d,c,h=0,p=s.length-1,g=0,u=r.length-1;for(;h<=p&&g<=u;)if(null===s[h])h++;else if(null===s[p])p--;else if(n[h]===a[g])l[g]=xe(s[h],r[g]),h++,g++;else if(n[p]===a[u])l[u]=xe(s[p],r[u]),p--,u--;else if(n[h]===a[u])l[u]=xe(s[h],r[u]),ye(e,l[u+1],s[h]),h++,u--;else if(n[p]===a[g])l[g]=xe(s[p],r[g]),ye(e,s[h],s[p]),p--,g++;else if(void 0===d&&(d=Ce(a,g,u),c=Ce(n,h,p)),d.has(n[h]))if(d.has(n[p])){const t=c.get(a[g]),i=void 0!==t?s[t]:null;if(null===i){const t=ye(e,s[h]);xe(t,r[g]),l[g]=t}else l[g]=xe(i,r[g]),ye(e,s[h],i),s[t]=null;g++}else De(s[p]),p--;else De(s[h]),h++;for(;g<=u;){const t=ye(e,l[u+1]);xe(t,r[g]),l[g++]=t}for(;h<=p;){const e=s[h++];null!==e&&De(e)}return this.ut=a,$e(e,l),B}});function Ee(e,t,i){return(t=function(e){var t=function(e,t){if("object"!=typeof e||!e)return e;var i=e[Symbol.toPrimitive];if(void 0!==i){var o=i.call(e,t);if("object"!=typeof o)return o;throw new TypeError("@@toPrimitive must return a primitive value.")}return String(e)}(e,"string");return"symbol"==typeof t?t:t+""}(t))in e?Object.defineProperty(e,t,{value:i,enumerable:!0,configurable:!0,writable:!0}):e[t]=i,e}function Ae(){return Ae=Object.assign?Object.assign.bind():function(e){for(var t=1;t<arguments.length;t++){var i=arguments[t];for(var o in i)({}).hasOwnProperty.call(i,o)&&(e[o]=i[o])}return e},Ae.apply(null,arguments)}function Se(e,t){var i=Object.keys(e);if(Object.getOwnPropertySymbols){var o=Object.getOwnPropertySymbols(e);t&&(o=o.filter(function(t){return Object.getOwnPropertyDescriptor(e,t).enumerable})),i.push.apply(i,o)}return i}function Ie(e){for(var t=1;t<arguments.length;t++){var i=null!=arguments[t]?arguments[t]:{};t%2?Se(Object(i),!0).forEach(function(t){Ee(e,t,i[t])}):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(i)):Se(Object(i)).forEach(function(t){Object.defineProperty(e,t,Object.getOwnPropertyDescriptor(i,t))})}return e}function Me(e){return Me="function"==typeof Symbol&&"symbol"==typeof Symbol.iterator?function(e){return typeof e}:function(e){return e&&"function"==typeof Symbol&&e.constructor===Symbol&&e!==Symbol.prototype?"symbol":typeof e},Me(e)}function Ne(e){if("undefined"!=typeof window&&window.navigator)return!!navigator.userAgent.match(e)}var Pe=Ne(/(?:Trident.*rv[ :]?11\.|msie|iemobile|Windows Phone)/i),He=Ne(/Edge/i),Re=Ne(/firefox/i),Le=Ne(/safari/i)&&!Ne(/chrome/i)&&!Ne(/android/i),Oe=Ne(/iP(ad|od|hone)/i),ze=Ne(/chrome/i)&&Ne(/android/i),Ve={capture:!1,passive:!1};function Fe(e,t,i){e.addEventListener(t,i,!Pe&&Ve)}function Ue(e,t,i){e.removeEventListener(t,i,!Pe&&Ve)}function je(e,t){if(t){if(">"===t[0]&&(t=t.substring(1)),e)try{if(e.matches)return e.matches(t);if(e.msMatchesSelector)return e.msMatchesSelector(t);if(e.webkitMatchesSelector)return e.webkitMatchesSelector(t)}catch(e){return!1}return!1}}function Be(e){return e.host&&e!==document&&e.host.nodeType&&e.host!==e?e.host:e.parentNode}function Xe(e,t,i,o){if(e){i=i||document;do{if(null!=t&&(">"===t[0]?e.parentNode===i&&je(e,t):je(e,t))||o&&e===i)return e;if(e===i)break}while(e=Be(e))}return null}var qe,Ye=/\s+/g;function We(e,t,i){if(e&&t)if(e.classList)e.classList[i?"add":"remove"](t);else{var o=(" "+e.className+" ").replace(Ye," ").replace(" "+t+" "," ");e.className=(o+(i?" "+t:"")).replace(Ye," ")}}function Ze(e,t,i){var o=e&&e.style;if(o){if(void 0===i)return document.defaultView&&document.defaultView.getComputedStyle?i=document.defaultView.getComputedStyle(e,""):e.currentStyle&&(i=e.currentStyle),void 0===t?i:i[t];t in o||-1!==t.indexOf("webkit")||(t="-webkit-"+t),o[t]=i+("string"==typeof i?"":"px")}}function Ke(e,t){var i="";if("string"==typeof e)i=e;else do{var o=Ze(e,"transform");o&&"none"!==o&&(i=o+" "+i)}while(!t&&(e=e.parentNode));var s=window.DOMMatrix||window.WebKitCSSMatrix||window.CSSMatrix||window.MSCSSMatrix;return s&&new s(i)}function Ge(e,t,i){if(e){var o=e.getElementsByTagName(t),s=0,r=o.length;if(i)for(;s<r;s++)i(o[s],s);return o}return[]}function Je(){return document.scrollingElement||document.documentElement}function Qe(e,t,i,o,s){if(e.getBoundingClientRect||e===window){var r,a,n,l,d,c,h;if(e!==window&&e.parentNode&&e!==Je()?(a=(r=e.getBoundingClientRect()).top,n=r.left,l=r.bottom,d=r.right,c=r.height,h=r.width):(a=0,n=0,l=window.innerHeight,d=window.innerWidth,c=window.innerHeight,h=window.innerWidth),(t||i)&&e!==window&&(s=s||e.parentNode,!Pe))do{if(s&&s.getBoundingClientRect&&("none"!==Ze(s,"transform")||i&&"static"!==Ze(s,"position"))){var p=s.getBoundingClientRect();a-=p.top+parseInt(Ze(s,"border-top-width")),n-=p.left+parseInt(Ze(s,"border-left-width")),l=a+r.height,d=n+r.width;break}}while(s=s.parentNode);if(o&&e!==window){var g=Ke(s||e),u=g&&g.a,m=g&&g.d;g&&(l=(a/=m)+(c/=m),d=(n/=u)+(h/=u))}return{top:a,left:n,bottom:l,right:d,width:h,height:c}}}function et(e,t,i){for(var o=rt(e,!0),s=Qe(e)[t];o;){if(!(s>=Qe(o)[i]))return o;if(o===Je())break;o=rt(o,!1)}return!1}function tt(e,t,i,o){for(var s=0,r=0,a=e.children;r<a.length;){if("none"!==a[r].style.display&&a[r]!==li.ghost&&(o||a[r]!==li.dragged)&&Xe(a[r],i.draggable,e,!1)){if(s===t)return a[r];s++}r++}return null}function it(e,t){for(var i=e.lastElementChild;i&&(i===li.ghost||"none"===Ze(i,"display")||t&&!je(i,t));)i=i.previousElementSibling;return i||null}function ot(e,t){var i=0;if(!e||!e.parentNode)return-1;for(;e=e.previousElementSibling;)"TEMPLATE"===e.nodeName.toUpperCase()||e===li.clone||t&&!je(e,t)||i++;return i}function st(e){var t=0,i=0,o=Je();if(e)do{var s=Ke(e),r=s.a,a=s.d;t+=e.scrollLeft*r,i+=e.scrollTop*a}while(e!==o&&(e=e.parentNode));return[t,i]}function rt(e,t){if(!e||!e.getBoundingClientRect)return Je();var i=e,o=!1;do{if(i.clientWidth<i.scrollWidth||i.clientHeight<i.scrollHeight){var s=Ze(i);if(i.clientWidth<i.scrollWidth&&("auto"==s.overflowX||"scroll"==s.overflowX)||i.clientHeight<i.scrollHeight&&("auto"==s.overflowY||"scroll"==s.overflowY)){if(!i.getBoundingClientRect||i===document.body)return Je();if(o||t)return i;o=!0}}}while(i=i.parentNode);return Je()}function at(e,t){return Math.round(e.top)===Math.round(t.top)&&Math.round(e.left)===Math.round(t.left)&&Math.round(e.height)===Math.round(t.height)&&Math.round(e.width)===Math.round(t.width)}function nt(e,t){return function(){if(!qe){var i=arguments;1===i.length?e.call(this,i[0]):e.apply(this,i),qe=setTimeout(function(){qe=void 0},t)}}}function lt(e,t,i){e.scrollLeft+=t,e.scrollTop+=i}function dt(e){var t=window.Polymer,i=window.jQuery||window.Zepto;return t&&t.dom?t.dom(e).cloneNode(!0):i?i(e).clone(!0)[0]:e.cloneNode(!0)}function ct(e,t,i){var o={};return Array.from(e.children).forEach(function(s){var r,a,n,l;if(Xe(s,t.draggable,e,!1)&&!s.animated&&s!==i){var d=Qe(s);o.left=Math.min(null!==(r=o.left)&&void 0!==r?r:1/0,d.left),o.top=Math.min(null!==(a=o.top)&&void 0!==a?a:1/0,d.top),o.right=Math.max(null!==(n=o.right)&&void 0!==n?n:-1/0,d.right),o.bottom=Math.max(null!==(l=o.bottom)&&void 0!==l?l:-1/0,d.bottom)}}),o.width=o.right-o.left,o.height=o.bottom-o.top,o.x=o.left,o.y=o.top,o}var ht="Sortable"+(new Date).getTime();var pt=[],gt={initializeByDefault:!0},ut={mount:function(e){for(var t in gt)gt.hasOwnProperty(t)&&!(t in e)&&(e[t]=gt[t]);pt.forEach(function(t){if(t.pluginName===e.pluginName)throw"Sortable: Cannot mount plugin ".concat(e.pluginName," more than once")}),pt.push(e)},pluginEvent:function(e,t,i){var o=this;this.eventCanceled=!1,i.cancel=function(){o.eventCanceled=!0};var s=e+"Global";pt.forEach(function(o){t[o.pluginName]&&(t[o.pluginName][s]&&t[o.pluginName][s](Ie({sortable:t},i)),t.options[o.pluginName]&&t[o.pluginName][e]&&t[o.pluginName][e](Ie({sortable:t},i)))})},initializePlugins:function(e,t,i,o){for(var s in pt.forEach(function(o){var s=o.pluginName;if(e.options[s]||o.initializeByDefault){var r=new o(e,t,e.options);r.sortable=e,r.options=e.options,e[s]=r,Ae(i,r.defaults)}}),e.options)if(e.options.hasOwnProperty(s)){var r=this.modifyOption(e,s,e.options[s]);void 0!==r&&(e.options[s]=r)}},getEventProperties:function(e,t){var i={};return pt.forEach(function(o){"function"==typeof o.eventProperties&&Ae(i,o.eventProperties.call(t[o.pluginName],e))}),i},modifyOption:function(e,t,i){var o;return pt.forEach(function(s){e[s.pluginName]&&s.optionListeners&&"function"==typeof s.optionListeners[t]&&(o=s.optionListeners[t].call(e[s.pluginName],i))}),o}},mt=["evt"],vt=function(e,t){var i=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},o=i.evt,s=function(e,t){if(null==e)return{};var i,o,s=function(e,t){if(null==e)return{};var i={};for(var o in e)if({}.hasOwnProperty.call(e,o)){if(-1!==t.indexOf(o))continue;i[o]=e[o]}return i}(e,t);if(Object.getOwnPropertySymbols){var r=Object.getOwnPropertySymbols(e);for(o=0;o<r.length;o++)i=r[o],-1===t.indexOf(i)&&{}.propertyIsEnumerable.call(e,i)&&(s[i]=e[i])}return s}(i,mt);ut.pluginEvent.bind(li)(e,t,Ie({dragEl:bt,parentEl:ft,ghostEl:yt,rootEl:xt,nextEl:wt,lastDownEl:$t,cloneEl:Dt,cloneHidden:kt,dragStarted:Ot,putSortable:It,activeSortable:li.active,originalEvent:o,oldIndex:Ct,oldDraggableIndex:Et,newIndex:Tt,newDraggableIndex:At,hideGhostForTarget:si,unhideGhostForTarget:ri,cloneNowHidden:function(){kt=!0},cloneNowShown:function(){kt=!1},dispatchSortableEvent:function(e){_t({sortable:t,name:e,originalEvent:o})}},s))};function _t(e){!function(e){var t=e.sortable,i=e.rootEl,o=e.name,s=e.targetEl,r=e.cloneEl,a=e.toEl,n=e.fromEl,l=e.oldIndex,d=e.newIndex,c=e.oldDraggableIndex,h=e.newDraggableIndex,p=e.originalEvent,g=e.putSortable,u=e.extraEventProperties;if(t=t||i&&i[ht]){var m,v=t.options,_="on"+o.charAt(0).toUpperCase()+o.substr(1);!window.CustomEvent||Pe||He?(m=document.createEvent("Event")).initEvent(o,!0,!0):m=new CustomEvent(o,{bubbles:!0,cancelable:!0}),m.to=a||i,m.from=n||i,m.item=s||i,m.clone=r,m.oldIndex=l,m.newIndex=d,m.oldDraggableIndex=c,m.newDraggableIndex=h,m.originalEvent=p,m.pullMode=g?g.lastPutMode:void 0;var b=Ie(Ie({},u),ut.getEventProperties(o,t));for(var f in b)m[f]=b[f];i&&i.dispatchEvent(m),v[_]&&v[_].call(t,m)}}(Ie({putSortable:It,cloneEl:Dt,targetEl:bt,rootEl:xt,oldIndex:Ct,oldDraggableIndex:Et,newIndex:Tt,newDraggableIndex:At},e))}var bt,ft,yt,xt,wt,$t,Dt,kt,Ct,Tt,Et,At,St,It,Mt,Nt,Pt,Ht,Rt,Lt,Ot,zt,Vt,Ft,Ut,jt=!1,Bt=!1,Xt=[],qt=!1,Yt=!1,Wt=[],Zt=!1,Kt=[],Gt="undefined"!=typeof document,Jt=Oe,Qt=He||Pe?"cssFloat":"float",ei=Gt&&!ze&&!Oe&&"draggable"in document.createElement("div"),ti=function(){if(Gt){if(Pe)return!1;var e=document.createElement("x");return e.style.cssText="pointer-events:auto","auto"===e.style.pointerEvents}}(),ii=function(e,t){var i=Ze(e),o=parseInt(i.width)-parseInt(i.paddingLeft)-parseInt(i.paddingRight)-parseInt(i.borderLeftWidth)-parseInt(i.borderRightWidth),s=tt(e,0,t),r=tt(e,1,t),a=s&&Ze(s),n=r&&Ze(r),l=a&&parseInt(a.marginLeft)+parseInt(a.marginRight)+Qe(s).width,d=n&&parseInt(n.marginLeft)+parseInt(n.marginRight)+Qe(r).width;if("flex"===i.display)return"column"===i.flexDirection||"column-reverse"===i.flexDirection?"vertical":"horizontal";if("grid"===i.display)return i.gridTemplateColumns.split(" ").length<=1?"vertical":"horizontal";if(s&&a.float&&"none"!==a.float){var c="left"===a.float?"left":"right";return!r||"both"!==n.clear&&n.clear!==c?"horizontal":"vertical"}return s&&("block"===a.display||"flex"===a.display||"table"===a.display||"grid"===a.display||l>=o&&"none"===i[Qt]||r&&"none"===i[Qt]&&l+d>o)?"vertical":"horizontal"},oi=function(e){function t(e,i){return function(o,s,r,a){var n=o.options.group.name&&s.options.group.name&&o.options.group.name===s.options.group.name;if(null==e&&(i||n))return!0;if(null==e||!1===e)return!1;if(i&&"clone"===e)return e;if("function"==typeof e)return t(e(o,s,r,a),i)(o,s,r,a);var l=(i?o:s).options.group.name;return!0===e||"string"==typeof e&&e===l||e.join&&e.indexOf(l)>-1}}var i={},o=e.group;o&&"object"==Me(o)||(o={name:o}),i.name=o.name,i.checkPull=t(o.pull,!0),i.checkPut=t(o.put),i.revertClone=o.revertClone,e.group=i},si=function(){!ti&&yt&&Ze(yt,"display","none")},ri=function(){!ti&&yt&&Ze(yt,"display","")};Gt&&!ze&&document.addEventListener("click",function(e){if(Bt)return e.preventDefault(),e.stopPropagation&&e.stopPropagation(),e.stopImmediatePropagation&&e.stopImmediatePropagation(),Bt=!1,!1},!0);var ai=function(e){if(bt){var t=function(e,t){var i;return Xt.some(function(o){var s=o[ht].options.emptyInsertThreshold;if(s&&!it(o)){var r=Qe(o),a=e>=r.left-s&&e<=r.right+s,n=t>=r.top-s&&t<=r.bottom+s;return a&&n?i=o:void 0}}),i}((e=e.touches?e.touches[0]:e).clientX,e.clientY);if(t){var i={};for(var o in e)e.hasOwnProperty(o)&&(i[o]=e[o]);i.target=i.rootEl=t,i.preventDefault=void 0,i.stopPropagation=void 0,t[ht]._onDragOver(i)}}},ni=function(e){bt&&bt.parentNode[ht]._isOutsideThisEl(e.target)};function li(e,t){if(!e||!e.nodeType||1!==e.nodeType)throw"Sortable: `el` must be an HTMLElement, not ".concat({}.toString.call(e));this.el=e,this.options=t=Ae({},t),e[ht]=this;var i,o,s={group:null,sort:!0,disabled:!1,store:null,handle:null,draggable:/^[uo]l$/i.test(e.nodeName)?">li":">*",swapThreshold:1,invertSwap:!1,invertedSwapThreshold:null,removeCloneOnHide:!0,direction:function(){return ii(e,this.options)},ghostClass:"sortable-ghost",chosenClass:"sortable-chosen",dragClass:"sortable-drag",ignore:"a, img",filter:null,preventOnFilter:!0,animation:0,easing:null,setData:function(e,t){e.setData("Text",t.textContent)},dropBubble:!1,dragoverBubble:!1,dataIdAttr:"data-id",delay:0,delayOnTouchOnly:!1,touchStartThreshold:(Number.parseInt?Number:window).parseInt(window.devicePixelRatio,10)||1,forceFallback:!1,fallbackClass:"sortable-fallback",fallbackOnBody:!1,fallbackTolerance:0,fallbackOffset:{x:0,y:0},supportPointer:!1!==li.supportPointer&&"PointerEvent"in window&&(!Le||Oe),emptyInsertThreshold:5};for(var r in ut.initializePlugins(this,e,s),s)!(r in t)&&(t[r]=s[r]);for(var a in oi(t),this)"_"===a.charAt(0)&&"function"==typeof this[a]&&(this[a]=this[a].bind(this));this.nativeDraggable=!t.forceFallback&&ei,this.nativeDraggable&&(this.options.touchStartThreshold=1),t.supportPointer?Fe(e,"pointerdown",this._onTapStart):(Fe(e,"mousedown",this._onTapStart),Fe(e,"touchstart",this._onTapStart)),this.nativeDraggable&&(Fe(e,"dragover",this),Fe(e,"dragenter",this)),Xt.push(this.el),t.store&&t.store.get&&this.sort(t.store.get(this)||[]),Ae(this,(o=[],{captureAnimationState:function(){o=[],this.options.animation&&[].slice.call(this.el.children).forEach(function(e){if("none"!==Ze(e,"display")&&e!==li.ghost){o.push({target:e,rect:Qe(e)});var t=Ie({},o[o.length-1].rect);if(e.thisAnimationDuration){var i=Ke(e,!0);i&&(t.top-=i.f,t.left-=i.e)}e.fromRect=t}})},addAnimationState:function(e){o.push(e)},removeAnimationState:function(e){o.splice(function(e,t){for(var i in e)if(e.hasOwnProperty(i))for(var o in t)if(t.hasOwnProperty(o)&&t[o]===e[i][o])return Number(i);return-1}(o,{target:e}),1)},animateAll:function(e){var t=this;if(!this.options.animation)return clearTimeout(i),void("function"==typeof e&&e());var s=!1,r=0;o.forEach(function(e){var i=0,o=e.target,a=o.fromRect,n=Qe(o),l=o.prevFromRect,d=o.prevToRect,c=e.rect,h=Ke(o,!0);h&&(n.top-=h.f,n.left-=h.e),o.toRect=n,o.thisAnimationDuration&&at(l,n)&&!at(a,n)&&(c.top-n.top)/(c.left-n.left)===(a.top-n.top)/(a.left-n.left)&&(i=function(e,t,i,o){return Math.sqrt(Math.pow(t.top-e.top,2)+Math.pow(t.left-e.left,2))/Math.sqrt(Math.pow(t.top-i.top,2)+Math.pow(t.left-i.left,2))*o.animation}(c,l,d,t.options)),at(n,a)||(o.prevFromRect=a,o.prevToRect=n,i||(i=t.options.animation),t.animate(o,c,n,i)),i&&(s=!0,r=Math.max(r,i),clearTimeout(o.animationResetTimer),o.animationResetTimer=setTimeout(function(){o.animationTime=0,o.prevFromRect=null,o.fromRect=null,o.prevToRect=null,o.thisAnimationDuration=null},i),o.thisAnimationDuration=i)}),clearTimeout(i),s?i=setTimeout(function(){"function"==typeof e&&e()},r):"function"==typeof e&&e(),o=[]},animate:function(e,t,i,o){if(o){Ze(e,"transition",""),Ze(e,"transform","");var s=Ke(this.el),r=s&&s.a,a=s&&s.d,n=(t.left-i.left)/(r||1),l=(t.top-i.top)/(a||1);e.animatingX=!!n,e.animatingY=!!l,Ze(e,"transform","translate3d("+n+"px,"+l+"px,0)"),this.forRepaintDummy=function(e){return e.offsetWidth}(e),Ze(e,"transition","transform "+o+"ms"+(this.options.easing?" "+this.options.easing:"")),Ze(e,"transform","translate3d(0,0,0)"),"number"==typeof e.animated&&clearTimeout(e.animated),e.animated=setTimeout(function(){Ze(e,"transition",""),Ze(e,"transform",""),e.animated=!1,e.animatingX=!1,e.animatingY=!1},o)}}}))}function di(e,t,i,o,s,r,a,n){var l,d,c=e[ht],h=c.options.onMove;return!window.CustomEvent||Pe||He?(l=document.createEvent("Event")).initEvent("move",!0,!0):l=new CustomEvent("move",{bubbles:!0,cancelable:!0}),l.to=t,l.from=e,l.dragged=i,l.draggedRect=o,l.related=s||t,l.relatedRect=r||Qe(t),l.willInsertAfter=n,l.originalEvent=a,e.dispatchEvent(l),h&&(d=h.call(c,l,a)),d}function ci(e){e.draggable=!1}function hi(){Zt=!1}function pi(e){for(var t=e.tagName+e.className+e.src+e.href+e.textContent,i=t.length,o=0;i--;)o+=t.charCodeAt(i);return o.toString(36)}function gi(e){return setTimeout(e,0)}function ui(e){return clearTimeout(e)}li.prototype={constructor:li,_isOutsideThisEl:function(e){this.el.contains(e)||e===this.el||(zt=null)},_getDirection:function(e,t){return"function"==typeof this.options.direction?this.options.direction.call(this,e,t,bt):this.options.direction},_onTapStart:function(e){if(e.cancelable){var t=this,i=this.el,o=this.options,s=o.preventOnFilter,r=e.type,a=e.touches&&e.touches[0]||e.pointerType&&"touch"===e.pointerType&&e,n=(a||e).target,l=e.target.shadowRoot&&(e.path&&e.path[0]||e.composedPath&&e.composedPath()[0])||n,d=o.filter;if(function(e){Kt.length=0;for(var t=e.getElementsByTagName("input"),i=t.length;i--;){var o=t[i];o.checked&&Kt.push(o)}}(i),!bt&&!(/mousedown|pointerdown/.test(r)&&0!==e.button||o.disabled)&&!l.isContentEditable&&(this.nativeDraggable||!Le||!n||"SELECT"!==n.tagName.toUpperCase())&&!((n=Xe(n,o.draggable,i,!1))&&n.animated||$t===n)){if(Ct=ot(n),Et=ot(n,o.draggable),"function"==typeof d){if(d.call(this,e,n,this))return _t({sortable:t,rootEl:l,name:"filter",targetEl:n,toEl:i,fromEl:i}),vt("filter",t,{evt:e}),void(s&&e.preventDefault())}else if(d&&(d=d.split(",").some(function(o){if(o=Xe(l,o.trim(),i,!1))return _t({sortable:t,rootEl:o,name:"filter",targetEl:n,fromEl:i,toEl:i}),vt("filter",t,{evt:e}),!0})))return void(s&&e.preventDefault());o.handle&&!Xe(l,o.handle,i,!1)||this._prepareDragStart(e,a,n)}}},_prepareDragStart:function(e,t,i){var o,s=this,r=s.el,a=s.options,n=r.ownerDocument;if(i&&!bt&&i.parentNode===r){var l=Qe(i);if(xt=r,ft=(bt=i).parentNode,wt=bt.nextSibling,$t=i,St=a.group,li.dragged=bt,Mt={target:bt,clientX:(t||e).clientX,clientY:(t||e).clientY},Rt=Mt.clientX-l.left,Lt=Mt.clientY-l.top,this._lastX=(t||e).clientX,this._lastY=(t||e).clientY,bt.style["will-change"]="all",o=function(){vt("delayEnded",s,{evt:e}),li.eventCanceled?s._onDrop():(s._disableDelayedDragEvents(),!Re&&s.nativeDraggable&&(bt.draggable=!0),s._triggerDragStart(e,t),_t({sortable:s,name:"choose",originalEvent:e}),We(bt,a.chosenClass,!0))},a.ignore.split(",").forEach(function(e){Ge(bt,e.trim(),ci)}),Fe(n,"dragover",ai),Fe(n,"mousemove",ai),Fe(n,"touchmove",ai),a.supportPointer?(Fe(n,"pointerup",s._onDrop),!this.nativeDraggable&&Fe(n,"pointercancel",s._onDrop)):(Fe(n,"mouseup",s._onDrop),Fe(n,"touchend",s._onDrop),Fe(n,"touchcancel",s._onDrop)),Re&&this.nativeDraggable&&(this.options.touchStartThreshold=4,bt.draggable=!0),vt("delayStart",this,{evt:e}),!a.delay||a.delayOnTouchOnly&&!t||this.nativeDraggable&&(He||Pe))o();else{if(li.eventCanceled)return void this._onDrop();a.supportPointer?(Fe(n,"pointerup",s._disableDelayedDrag),Fe(n,"pointercancel",s._disableDelayedDrag)):(Fe(n,"mouseup",s._disableDelayedDrag),Fe(n,"touchend",s._disableDelayedDrag),Fe(n,"touchcancel",s._disableDelayedDrag)),Fe(n,"mousemove",s._delayedDragTouchMoveHandler),Fe(n,"touchmove",s._delayedDragTouchMoveHandler),a.supportPointer&&Fe(n,"pointermove",s._delayedDragTouchMoveHandler),s._dragStartTimer=setTimeout(o,a.delay)}}},_delayedDragTouchMoveHandler:function(e){var t=e.touches?e.touches[0]:e;Math.max(Math.abs(t.clientX-this._lastX),Math.abs(t.clientY-this._lastY))>=Math.floor(this.options.touchStartThreshold/(this.nativeDraggable&&window.devicePixelRatio||1))&&this._disableDelayedDrag()},_disableDelayedDrag:function(){bt&&ci(bt),clearTimeout(this._dragStartTimer),this._disableDelayedDragEvents()},_disableDelayedDragEvents:function(){var e=this.el.ownerDocument;Ue(e,"mouseup",this._disableDelayedDrag),Ue(e,"touchend",this._disableDelayedDrag),Ue(e,"touchcancel",this._disableDelayedDrag),Ue(e,"pointerup",this._disableDelayedDrag),Ue(e,"pointercancel",this._disableDelayedDrag),Ue(e,"mousemove",this._delayedDragTouchMoveHandler),Ue(e,"touchmove",this._delayedDragTouchMoveHandler),Ue(e,"pointermove",this._delayedDragTouchMoveHandler)},_triggerDragStart:function(e,t){t=t||"touch"==e.pointerType&&e,!this.nativeDraggable||t?this.options.supportPointer?Fe(document,"pointermove",this._onTouchMove):Fe(document,t?"touchmove":"mousemove",this._onTouchMove):(Fe(bt,"dragend",this),Fe(xt,"dragstart",this._onDragStart));try{document.selection?gi(function(){document.selection.empty()}):window.getSelection().removeAllRanges()}catch(e){}},_dragStarted:function(e,t){if(jt=!1,xt&&bt){vt("dragStarted",this,{evt:t}),this.nativeDraggable&&Fe(document,"dragover",ni);var i=this.options;!e&&We(bt,i.dragClass,!1),We(bt,i.ghostClass,!0),li.active=this,e&&this._appendGhost(),_t({sortable:this,name:"start",originalEvent:t})}else this._nulling()},_emulateDragOver:function(){if(Nt){this._lastX=Nt.clientX,this._lastY=Nt.clientY,si();for(var e=document.elementFromPoint(Nt.clientX,Nt.clientY),t=e;e&&e.shadowRoot&&(e=e.shadowRoot.elementFromPoint(Nt.clientX,Nt.clientY))!==t;)t=e;if(bt.parentNode[ht]._isOutsideThisEl(e),t)do{if(t[ht]&&t[ht]._onDragOver({clientX:Nt.clientX,clientY:Nt.clientY,target:e,rootEl:t})&&!this.options.dragoverBubble)break;e=t}while(t=Be(t));ri()}},_onTouchMove:function(e){if(Mt){var t=this.options,i=t.fallbackTolerance,o=t.fallbackOffset,s=e.touches?e.touches[0]:e,r=yt&&Ke(yt,!0),a=yt&&r&&r.a,n=yt&&r&&r.d,l=Jt&&Ut&&st(Ut),d=(s.clientX-Mt.clientX+o.x)/(a||1)+(l?l[0]-Wt[0]:0)/(a||1),c=(s.clientY-Mt.clientY+o.y)/(n||1)+(l?l[1]-Wt[1]:0)/(n||1);if(!li.active&&!jt){if(i&&Math.max(Math.abs(s.clientX-this._lastX),Math.abs(s.clientY-this._lastY))<i)return;this._onDragStart(e,!0)}if(yt){r?(r.e+=d-(Pt||0),r.f+=c-(Ht||0)):r={a:1,b:0,c:0,d:1,e:d,f:c};var h="matrix(".concat(r.a,",").concat(r.b,",").concat(r.c,",").concat(r.d,",").concat(r.e,",").concat(r.f,")");Ze(yt,"webkitTransform",h),Ze(yt,"mozTransform",h),Ze(yt,"msTransform",h),Ze(yt,"transform",h),Pt=d,Ht=c,Nt=s}e.cancelable&&e.preventDefault()}},_appendGhost:function(){if(!yt){var e=this.options.fallbackOnBody?document.body:xt,t=Qe(bt,!0,Jt,!0,e),i=this.options;if(Jt){for(Ut=e;"static"===Ze(Ut,"position")&&"none"===Ze(Ut,"transform")&&Ut!==document;)Ut=Ut.parentNode;Ut!==document.body&&Ut!==document.documentElement?(Ut===document&&(Ut=Je()),t.top+=Ut.scrollTop,t.left+=Ut.scrollLeft):Ut=Je(),Wt=st(Ut)}We(yt=bt.cloneNode(!0),i.ghostClass,!1),We(yt,i.fallbackClass,!0),We(yt,i.dragClass,!0),Ze(yt,"transition",""),Ze(yt,"transform",""),Ze(yt,"box-sizing","border-box"),Ze(yt,"margin",0),Ze(yt,"top",t.top),Ze(yt,"left",t.left),Ze(yt,"width",t.width),Ze(yt,"height",t.height),Ze(yt,"opacity","0.8"),Ze(yt,"position",Jt?"absolute":"fixed"),Ze(yt,"zIndex","100000"),Ze(yt,"pointerEvents","none"),li.ghost=yt,e.appendChild(yt),Ze(yt,"transform-origin",Rt/parseInt(yt.style.width)*100+"% "+Lt/parseInt(yt.style.height)*100+"%")}},_onDragStart:function(e,t){var i=this,o=e.dataTransfer,s=i.options;vt("dragStart",this,{evt:e}),li.eventCanceled?this._onDrop():(vt("setupClone",this),li.eventCanceled||((Dt=dt(bt)).removeAttribute("id"),Dt.draggable=!1,Dt.style["will-change"]="",this._hideClone(),We(Dt,this.options.chosenClass,!1),li.clone=Dt),i.cloneId=gi(function(){vt("clone",i),li.eventCanceled||(i.options.removeCloneOnHide||xt.insertBefore(Dt,bt),i._hideClone(),_t({sortable:i,name:"clone"}))}),!t&&We(bt,s.dragClass,!0),t?(Bt=!0,i._loopId=setInterval(i._emulateDragOver,50)):(Ue(document,"mouseup",i._onDrop),Ue(document,"touchend",i._onDrop),Ue(document,"touchcancel",i._onDrop),o&&(o.effectAllowed="move",s.setData&&s.setData.call(i,o,bt)),Fe(document,"drop",i),Ze(bt,"transform","translateZ(0)")),jt=!0,i._dragStartId=gi(i._dragStarted.bind(i,t,e)),Fe(document,"selectstart",i),Ot=!0,window.getSelection().removeAllRanges(),Le&&Ze(document.body,"user-select","none"))},_onDragOver:function(e){var t,i,o,s,r=this.el,a=e.target,n=this.options,l=n.group,d=li.active,c=St===l,h=n.sort,p=It||d,g=this,u=!1;if(!Zt){if(void 0!==e.preventDefault&&e.cancelable&&e.preventDefault(),a=Xe(a,n.draggable,r,!0),A("dragOver"),li.eventCanceled)return u;if(bt.contains(e.target)||a.animated&&a.animatingX&&a.animatingY||g._ignoreWhileAnimating===a)return I(!1);if(Bt=!1,d&&!n.disabled&&(c?h||(o=ft!==xt):It===this||(this.lastPutMode=St.checkPull(this,d,bt,e))&&l.checkPut(this,d,bt,e))){if(s="vertical"===this._getDirection(e,a),t=Qe(bt),A("dragOverValid"),li.eventCanceled)return u;if(o)return ft=xt,S(),this._hideClone(),A("revert"),li.eventCanceled||(wt?xt.insertBefore(bt,wt):xt.appendChild(bt)),I(!0);var m=it(r,n.draggable);if(!m||function(e,t,i){var o=Qe(it(i.el,i.options.draggable)),s=ct(i.el,i.options,yt);return t?e.clientX>s.right+10||e.clientY>o.bottom&&e.clientX>o.left:e.clientY>s.bottom+10||e.clientX>o.right&&e.clientY>o.top}(e,s,this)&&!m.animated){if(m===bt)return I(!1);if(m&&r===e.target&&(a=m),a&&(i=Qe(a)),!1!==di(xt,r,bt,t,a,i,e,!!a))return S(),m&&m.nextSibling?r.insertBefore(bt,m.nextSibling):r.appendChild(bt),ft=r,M(),I(!0)}else if(m&&function(e,t,i){var o=Qe(tt(i.el,0,i.options,!0)),s=ct(i.el,i.options,yt);return t?e.clientX<s.left-10||e.clientY<o.top&&e.clientX<o.right:e.clientY<s.top-10||e.clientY<o.bottom&&e.clientX<o.left}(e,s,this)){var v=tt(r,0,n,!0);if(v===bt)return I(!1);if(i=Qe(a=v),!1!==di(xt,r,bt,t,a,i,e,!1))return S(),r.insertBefore(bt,v),ft=r,M(),I(!0)}else if(a.parentNode===r){i=Qe(a);var _,b,f,y=bt.parentNode!==r,x=!function(e,t,i){var o=i?e.left:e.top,s=i?e.right:e.bottom,r=i?e.width:e.height,a=i?t.left:t.top,n=i?t.right:t.bottom,l=i?t.width:t.height;return o===a||s===n||o+r/2===a+l/2}(bt.animated&&bt.toRect||t,a.animated&&a.toRect||i,s),w=s?"top":"left",$=et(a,"top","top")||et(bt,"top","top"),D=$?$.scrollTop:void 0;if(zt!==a&&(b=i[w],qt=!1,Yt=!x&&n.invertSwap||y),_=function(e,t,i,o,s,r,a,n){var l=o?e.clientY:e.clientX,d=o?i.height:i.width,c=o?i.top:i.left,h=o?i.bottom:i.right,p=!1;if(!a)if(n&&Ft<d*s){if(!qt&&(1===Vt?l>c+d*r/2:l<h-d*r/2)&&(qt=!0),qt)p=!0;else if(1===Vt?l<c+Ft:l>h-Ft)return-Vt}else if(l>c+d*(1-s)/2&&l<h-d*(1-s)/2)return function(e){return ot(bt)<ot(e)?1:-1}(t);return(p=p||a)&&(l<c+d*r/2||l>h-d*r/2)?l>c+d/2?1:-1:0}(e,a,i,s,x?1:n.swapThreshold,null==n.invertedSwapThreshold?n.swapThreshold:n.invertedSwapThreshold,Yt,zt===a),0!==_){var k=ot(bt);do{k-=_,f=ft.children[k]}while(f&&("none"===Ze(f,"display")||f===yt))}if(0===_||f===a)return I(!1);zt=a,Vt=_;var C=a.nextElementSibling,T=!1,E=di(xt,r,bt,t,a,i,e,T=1===_);if(!1!==E)return 1!==E&&-1!==E||(T=1===E),Zt=!0,setTimeout(hi,30),S(),T&&!C?r.appendChild(bt):a.parentNode.insertBefore(bt,T?C:a),$&&lt($,0,D-$.scrollTop),ft=bt.parentNode,void 0===b||Yt||(Ft=Math.abs(b-Qe(a)[w])),M(),I(!0)}if(r.contains(bt))return I(!1)}return!1}function A(n,l){vt(n,g,Ie({evt:e,isOwner:c,axis:s?"vertical":"horizontal",revert:o,dragRect:t,targetRect:i,canSort:h,fromSortable:p,target:a,completed:I,onMove:function(i,o){return di(xt,r,bt,t,i,Qe(i),e,o)},changed:M},l))}function S(){A("dragOverAnimationCapture"),g.captureAnimationState(),g!==p&&p.captureAnimationState()}function I(t){return A("dragOverCompleted",{insertion:t}),t&&(c?d._hideClone():d._showClone(g),g!==p&&(We(bt,It?It.options.ghostClass:d.options.ghostClass,!1),We(bt,n.ghostClass,!0)),It!==g&&g!==li.active?It=g:g===li.active&&It&&(It=null),p===g&&(g._ignoreWhileAnimating=a),g.animateAll(function(){A("dragOverAnimationComplete"),g._ignoreWhileAnimating=null}),g!==p&&(p.animateAll(),p._ignoreWhileAnimating=null)),(a===bt&&!bt.animated||a===r&&!a.animated)&&(zt=null),n.dragoverBubble||e.rootEl||a===document||(bt.parentNode[ht]._isOutsideThisEl(e.target),!t&&ai(e)),!n.dragoverBubble&&e.stopPropagation&&e.stopPropagation(),u=!0}function M(){Tt=ot(bt),At=ot(bt,n.draggable),_t({sortable:g,name:"change",toEl:r,newIndex:Tt,newDraggableIndex:At,originalEvent:e})}},_ignoreWhileAnimating:null,_offMoveEvents:function(){Ue(document,"mousemove",this._onTouchMove),Ue(document,"touchmove",this._onTouchMove),Ue(document,"pointermove",this._onTouchMove),Ue(document,"dragover",ai),Ue(document,"mousemove",ai),Ue(document,"touchmove",ai)},_offUpEvents:function(){var e=this.el.ownerDocument;Ue(e,"mouseup",this._onDrop),Ue(e,"touchend",this._onDrop),Ue(e,"pointerup",this._onDrop),Ue(e,"pointercancel",this._onDrop),Ue(e,"touchcancel",this._onDrop),Ue(document,"selectstart",this)},_onDrop:function(e){var t=this.el,i=this.options;Tt=ot(bt),At=ot(bt,i.draggable),vt("drop",this,{evt:e}),ft=bt&&bt.parentNode,Tt=ot(bt),At=ot(bt,i.draggable),li.eventCanceled||(jt=!1,Yt=!1,qt=!1,clearInterval(this._loopId),clearTimeout(this._dragStartTimer),ui(this.cloneId),ui(this._dragStartId),this.nativeDraggable&&(Ue(document,"drop",this),Ue(t,"dragstart",this._onDragStart)),this._offMoveEvents(),this._offUpEvents(),Le&&Ze(document.body,"user-select",""),Ze(bt,"transform",""),e&&(Ot&&(e.cancelable&&e.preventDefault(),!i.dropBubble&&e.stopPropagation()),yt&&yt.parentNode&&yt.parentNode.removeChild(yt),(xt===ft||It&&"clone"!==It.lastPutMode)&&Dt&&Dt.parentNode&&Dt.parentNode.removeChild(Dt),bt&&(this.nativeDraggable&&Ue(bt,"dragend",this),ci(bt),bt.style["will-change"]="",Ot&&!jt&&We(bt,It?It.options.ghostClass:this.options.ghostClass,!1),We(bt,this.options.chosenClass,!1),_t({sortable:this,name:"unchoose",toEl:ft,newIndex:null,newDraggableIndex:null,originalEvent:e}),xt!==ft?(Tt>=0&&(_t({rootEl:ft,name:"add",toEl:ft,fromEl:xt,originalEvent:e}),_t({sortable:this,name:"remove",toEl:ft,originalEvent:e}),_t({rootEl:ft,name:"sort",toEl:ft,fromEl:xt,originalEvent:e}),_t({sortable:this,name:"sort",toEl:ft,originalEvent:e})),It&&It.save()):Tt!==Ct&&Tt>=0&&(_t({sortable:this,name:"update",toEl:ft,originalEvent:e}),_t({sortable:this,name:"sort",toEl:ft,originalEvent:e})),li.active&&(null!=Tt&&-1!==Tt||(Tt=Ct,At=Et),_t({sortable:this,name:"end",toEl:ft,originalEvent:e}),this.save())))),this._nulling()},_nulling:function(){vt("nulling",this),xt=bt=ft=yt=wt=Dt=$t=kt=Mt=Nt=Ot=Tt=At=Ct=Et=zt=Vt=It=St=li.dragged=li.ghost=li.clone=li.active=null;var e=this.el;Kt.forEach(function(t){e.contains(t)&&(t.checked=!0)}),Kt.length=Pt=Ht=0},handleEvent:function(e){switch(e.type){case"drop":case"dragend":this._onDrop(e);break;case"dragenter":case"dragover":bt&&(this._onDragOver(e),function(e){e.dataTransfer&&(e.dataTransfer.dropEffect="move"),e.cancelable&&e.preventDefault()}(e));break;case"selectstart":e.preventDefault()}},toArray:function(){for(var e,t=[],i=this.el.children,o=0,s=i.length,r=this.options;o<s;o++)Xe(e=i[o],r.draggable,this.el,!1)&&t.push(e.getAttribute(r.dataIdAttr)||pi(e));return t},sort:function(e,t){var i={},o=this.el;this.toArray().forEach(function(e,t){var s=o.children[t];Xe(s,this.options.draggable,o,!1)&&(i[e]=s)},this),t&&this.captureAnimationState(),e.forEach(function(e){i[e]&&(o.removeChild(i[e]),o.appendChild(i[e]))}),t&&this.animateAll()},save:function(){var e=this.options.store;e&&e.set&&e.set(this)},closest:function(e,t){return Xe(e,t||this.options.draggable,this.el,!1)},option:function(e,t){var i=this.options;if(void 0===t)return i[e];var o=ut.modifyOption(this,e,t);i[e]=void 0!==o?o:t,"group"===e&&oi(i)},destroy:function(){vt("destroy",this);var e=this.el;e[ht]=null,Ue(e,"mousedown",this._onTapStart),Ue(e,"touchstart",this._onTapStart),Ue(e,"pointerdown",this._onTapStart),this.nativeDraggable&&(Ue(e,"dragover",this),Ue(e,"dragenter",this)),Array.prototype.forEach.call(e.querySelectorAll("[draggable]"),function(e){e.removeAttribute("draggable")}),this._onDrop(),this._disableDelayedDragEvents(),Xt.splice(Xt.indexOf(this.el),1),this.el=e=null},_hideClone:function(){if(!kt){if(vt("hideClone",this),li.eventCanceled)return;Ze(Dt,"display","none"),this.options.removeCloneOnHide&&Dt.parentNode&&Dt.parentNode.removeChild(Dt),kt=!0}},_showClone:function(e){if("clone"===e.lastPutMode){if(kt){if(vt("showClone",this),li.eventCanceled)return;bt.parentNode!=xt||this.options.group.revertClone?wt?xt.insertBefore(Dt,wt):xt.appendChild(Dt):xt.insertBefore(Dt,bt),this.options.group.revertClone&&this.animate(bt,Dt),Ze(Dt,"display",""),kt=!1}}else this._hideClone()}},Gt&&Fe(document,"touchmove",function(e){(li.active||jt)&&e.cancelable&&e.preventDefault()}),li.utils={on:Fe,off:Ue,css:Ze,find:Ge,is:function(e,t){return!!Xe(e,t,e,!1)},extend:function(e,t){if(e&&t)for(var i in t)t.hasOwnProperty(i)&&(e[i]=t[i]);return e},throttle:nt,closest:Xe,toggleClass:We,clone:dt,index:ot,nextTick:gi,cancelNextTick:ui,detectDirection:ii,getChild:tt,expando:ht},li.get=function(e){return e[ht]},li.mount=function(){for(var e=arguments.length,t=new Array(e),i=0;i<e;i++)t[i]=arguments[i];t[0].constructor===Array&&(t=t[0]),t.forEach(function(e){if(!e.prototype||!e.prototype.constructor)throw"Sortable: Mounted plugin must be a constructor function, not ".concat({}.toString.call(e));e.utils&&(li.utils=Ie(Ie({},li.utils),e.utils)),ut.mount(e)})},li.create=function(e,t){return new li(e,t)},li.version="1.15.7";var mi,vi,_i,bi,fi,yi,xi=[],wi=!1;function $i(){xi.forEach(function(e){clearInterval(e.pid)}),xi=[]}function Di(){clearInterval(yi)}var ki=nt(function(e,t,i,o){if(t.scroll){var s,r=(e.touches?e.touches[0]:e).clientX,a=(e.touches?e.touches[0]:e).clientY,n=t.scrollSensitivity,l=t.scrollSpeed,d=Je(),c=!1;vi!==i&&(vi=i,$i(),mi=t.scroll,s=t.scrollFn,!0===mi&&(mi=rt(i,!0)));var h=0,p=mi;do{var g=p,u=Qe(g),m=u.top,v=u.bottom,_=u.left,b=u.right,f=u.width,y=u.height,x=void 0,w=void 0,$=g.scrollWidth,D=g.scrollHeight,k=Ze(g),C=g.scrollLeft,T=g.scrollTop;g===d?(x=f<$&&("auto"===k.overflowX||"scroll"===k.overflowX||"visible"===k.overflowX),w=y<D&&("auto"===k.overflowY||"scroll"===k.overflowY||"visible"===k.overflowY)):(x=f<$&&("auto"===k.overflowX||"scroll"===k.overflowX),w=y<D&&("auto"===k.overflowY||"scroll"===k.overflowY));var E=x&&(Math.abs(b-r)<=n&&C+f<$)-(Math.abs(_-r)<=n&&!!C),A=w&&(Math.abs(v-a)<=n&&T+y<D)-(Math.abs(m-a)<=n&&!!T);if(!xi[h])for(var S=0;S<=h;S++)xi[S]||(xi[S]={});xi[h].vx==E&&xi[h].vy==A&&xi[h].el===g||(xi[h].el=g,xi[h].vx=E,xi[h].vy=A,clearInterval(xi[h].pid),0==E&&0==A||(c=!0,xi[h].pid=setInterval(function(){o&&0===this.layer&&li.active._onTouchMove(fi);var t=xi[this.layer].vy?xi[this.layer].vy*l:0,i=xi[this.layer].vx?xi[this.layer].vx*l:0;"function"==typeof s&&"continue"!==s.call(li.dragged.parentNode[ht],i,t,e,fi,xi[this.layer].el)||lt(xi[this.layer].el,i,t)}.bind({layer:h}),24))),h++}while(t.bubbleScroll&&p!==d&&(p=rt(p,!1)));wi=c}},30),Ci=function(e){var t=e.originalEvent,i=e.putSortable,o=e.dragEl,s=e.activeSortable,r=e.dispatchSortableEvent,a=e.hideGhostForTarget,n=e.unhideGhostForTarget;if(t){var l=i||s;a();var d=t.changedTouches&&t.changedTouches.length?t.changedTouches[0]:t,c=document.elementFromPoint(d.clientX,d.clientY);n(),l&&!l.el.contains(c)&&(r("spill"),this.onSpill({dragEl:o,putSortable:i}))}};function Ti(){}function Ei(){}Ti.prototype={startIndex:null,dragStart:function(e){var t=e.oldDraggableIndex;this.startIndex=t},onSpill:function(e){var t=e.dragEl,i=e.putSortable;this.sortable.captureAnimationState(),i&&i.captureAnimationState();var o=tt(this.sortable.el,this.startIndex,this.options);o?this.sortable.el.insertBefore(t,o):this.sortable.el.appendChild(t),this.sortable.animateAll(),i&&i.animateAll()},drop:Ci},Ae(Ti,{pluginName:"revertOnSpill"}),Ei.prototype={onSpill:function(e){var t=e.dragEl,i=e.putSortable||this.sortable;i.captureAnimationState(),t.parentNode&&t.parentNode.removeChild(t),i.animateAll()},drop:Ci},Ae(Ei,{pluginName:"removeOnSpill"}),li.mount(new function(){function e(){for(var e in this.defaults={scroll:!0,forceAutoScrollFallback:!1,scrollSensitivity:30,scrollSpeed:10,bubbleScroll:!0},this)"_"===e.charAt(0)&&"function"==typeof this[e]&&(this[e]=this[e].bind(this))}return e.prototype={dragStarted:function(e){var t=e.originalEvent;this.sortable.nativeDraggable?Fe(document,"dragover",this._handleAutoScroll):this.options.supportPointer?Fe(document,"pointermove",this._handleFallbackAutoScroll):t.touches?Fe(document,"touchmove",this._handleFallbackAutoScroll):Fe(document,"mousemove",this._handleFallbackAutoScroll)},dragOverCompleted:function(e){var t=e.originalEvent;this.options.dragOverBubble||t.rootEl||this._handleAutoScroll(t)},drop:function(){this.sortable.nativeDraggable?Ue(document,"dragover",this._handleAutoScroll):(Ue(document,"pointermove",this._handleFallbackAutoScroll),Ue(document,"touchmove",this._handleFallbackAutoScroll),Ue(document,"mousemove",this._handleFallbackAutoScroll)),Di(),$i(),clearTimeout(qe),qe=void 0},nulling:function(){fi=vi=mi=wi=yi=_i=bi=null,xi.length=0},_handleFallbackAutoScroll:function(e){this._handleAutoScroll(e,!0)},_handleAutoScroll:function(e,t){var i=this,o=(e.touches?e.touches[0]:e).clientX,s=(e.touches?e.touches[0]:e).clientY,r=document.elementFromPoint(o,s);if(fi=e,t||this.options.forceAutoScrollFallback||He||Pe||Le){ki(e,this.options,r,t);var a=rt(r,!0);!wi||yi&&o===_i&&s===bi||(yi&&Di(),yi=setInterval(function(){var r=rt(document.elementFromPoint(o,s),!0);r!==a&&(a=r,$i()),ki(e,i.options,r,t)},10),_i=o,bi=s)}else{if(!this.options.bubbleScroll||rt(r,!0)===Je())return void $i();ki(e,this.options,rt(r,!1),!1)}}},Ae(e,{pluginName:"scroll",initializeByDefault:!0})}),li.mount(Ei,Ti);let Ai=class extends ne{constructor(){super(...arguments),this.templateName="",this.command=null,this.busy=!1,this.actionLabel=null,this.hasTrigger=!1}_commandLabel(){const e=this.command;return e.protocol&&e.code?`${e.protocol}: ${e.code}`:e.raw_timings?.length?`RAW: ${e.raw_timings.length} timings`:e.protocol??"IR"}_prontoSlArray(e){const t=e.trim().split(/\s+/);if(t.length<6)return null;const i=parseInt(t[2],16)+parseInt(t[3],16),o=t.slice(4);if(o.length<2*i)return null;const s=[];for(let e=0;e<2*i;e++){const t=parseInt(o[e],16);s.push(t>=48)}return s.length>0?s:null}_renderDiamonds(){const e=this.command;if(!e||"PRONTO"!==e.protocol?.toUpperCase()||!e.code)return null;const t=this._prontoSlArray(e.code);return t?j`<span class="diamonds">${t.map(e=>e?j`<span class="diamond long">◆</span>`:j`<span class="diamond short">◇</span>`)}</span>`:null}_emit(e){this.dispatchEvent(new CustomEvent(e,{detail:{templateName:this.templateName,command:this.command},bubbles:!0,composed:!0}))}render(){const e=null!==this.command,t=e?this._renderDiamonds():null;return j`
            <div class="row" data-learned=${e?"true":"false"}>
                <div class="status" aria-hidden="true">
                    <slot name="status"></slot>
                </div>
                <div class="info">
                    <div class="name">${this.templateName}</div>
                    <div class="meta">
                        ${t||(e?j`${this._commandLabel()}`:j`<span class="muted">Not yet learned</span>`)}
                    </div>
                </div>
                <div class="actions">
                    ${e?j`
                              <button
                                  class="action-btn badge-btn"
                                  ?data-mapped=${!!this.actionLabel}
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("map-action")}
                                  title="Assign action mapping"
                              >${this.actionLabel||"ACTIONS"}</button>
                              <button
                                  class="action-btn test-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("test")}
                              >Test</button>
                              <button
                                  class="action-btn trigger-btn ${this.hasTrigger?"trigger-on":""}"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("toggle-trigger")}
                                  title=${this.hasTrigger?"Edit trigger":"Create trigger"}
                              >Trigger</button>
                              <button
                                  class="action-btn delete-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("delete")}
                              >Delete</button>
                          `:j`
                              <button
                                  class="action-btn learn-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("learn")}
                              >Learn</button>
                          `}
                </div>
            </div>
        `}};Ai.styles=a`
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
            background: var(--secondary-background-color);
            border-radius: 4px;
        }
        .status {
            display: flex;
            align-items: center;
            justify-content: center;
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
        .action-btn.badge-btn {
            color: var(--secondary-text-color, #999);
            border-color: var(--divider-color);
            font-size: 0.65rem;
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
            color: #b89930;
            border-color: rgba(184, 153, 48, 0.3);
        }
        .action-btn.trigger-btn:hover {
            background: rgba(184, 153, 48, 0.08);
        }
        .action-btn.trigger-btn.trigger-on {
            color: #fff;
            background: #b89930;
            border-color: #b89930;
        }
        .action-btn.trigger-btn.trigger-on:hover {
            background: #a08328;
        }
        .action-btn.delete-btn {
            color: #e65100;
            border-color: rgba(230, 81, 0, 0.25);
        }
        .action-btn.delete-btn:hover {
            background: rgba(230, 81, 0, 0.08);
        }
    `,e([pe({attribute:!1})],Ai.prototype,"templateName",void 0),e([pe({attribute:!1})],Ai.prototype,"command",void 0),e([pe({type:Boolean})],Ai.prototype,"busy",void 0),e([pe({attribute:!1})],Ai.prototype,"actionLabel",void 0),e([pe({type:Boolean})],Ai.prototype,"hasTrigger",void 0),Ai=e([de("ir-command-row")],Ai);let Si=class extends ne{constructor(){super(...arguments),this.commandName="",this.timeout=15,this._phase="listening",this._result=null,this._duplicate=null,this._error=null,this._timeRemaining=0,this._sessionId=null,this._unsubscribe=null,this._countdown=null}connectedCallback(){super.connectedCallback(),this._beginCapture()}disconnectedCallback(){super.disconnectedCallback(),this._stopCountdown(),this._unsubscribe&&(this._unsubscribe(),this._unsubscribe=null)}async _beginCapture(){this._phase="listening",this._result=null,this._duplicate=null,this._error=null,this._timeRemaining=this.timeout,this._startCountdown();try{const{session:e,unsubscribe:t}=await this.api.startCapture(this.device.id,this.timeout,e=>this._onCaptureEvent(e));this._sessionId=e.session_id,this._unsubscribe=t}catch(e){this._stopCountdown(),this._error=e.message,this._phase="error"}}_onCaptureEvent(e){switch(e.type){case"capture_listening":this._phase="listening";break;case"capture_received":this._stopCountdown(),this._result=e.result,e.duplicate_of?(this._duplicate=e.duplicate_of,this._phase="duplicate"):this._phase="captured";break;case"capture_timeout":this._stopCountdown(),this._phase="timeout";break;case"capture_error":this._stopCountdown(),this._error=e.error,this._phase="error";break;case"capture_cancelled":this._stopCountdown(),this._close()}}_startCountdown(){this._stopCountdown();const e=Date.now();this._countdown=window.setInterval(()=>{const t=(Date.now()-e)/1e3;this._timeRemaining=Math.max(0,Math.ceil(this.timeout-t)),this._timeRemaining<=0&&this._stopCountdown()},250)}_stopCountdown(){null!==this._countdown&&(clearInterval(this._countdown),this._countdown=null)}async _cancel(){if(this._sessionId)try{await this.api.cancelCapture(this._sessionId)}catch{}this._close()}async _testCommand(){if(!this._sessionId)return;const e=`__hair_test_${Date.now()}`;try{const t=await this.api.saveCapturedCommand({device_id:this.device.id,session_id:this._sessionId,command_name:e});await this.api.sendCommand(this.device.id,t.id),await this.api.deleteCommand(this.device.id,t.id)}catch(e){this._error=e.message,this._phase="error"}}async _save(e){if(this._sessionId)try{await this.api.saveCapturedCommand({device_id:this.device.id,session_id:this._sessionId,command_name:this.commandName}),this.dispatchEvent(new CustomEvent("command-saved",{detail:{saveAndNext:e,commandName:this.commandName},bubbles:!0,composed:!0})),this._close()}catch(e){this._error=e.message,this._phase="error"}}async _recapture(){this._unsubscribe&&(await this._unsubscribe(),this._unsubscribe=null),await this._beginCapture()}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_renderListening(){return j`
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
        `}_renderCaptured(){const e=this._result;return j`
            <div class="phase captured" aria-live="polite">
                <div class="check" aria-hidden="true">✓</div>
                <div class="title">Signal Captured!</div>
                <div class="meta">
                    Protocol: ${e.protocol??"Raw"}${e.code?j` · <code>${e.code}</code>`:""}
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
        `}_renderTimeout(){return j`
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
        `}_renderDuplicate(){const e=this._result;return j`
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
        `}_renderError(){return j`
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
        `}render(){return j`
            <ha-dialog
                open
                heading=${`Learning: "${this.commandName}"`}
                @closed=${this._cancel}
            >
                ${"listening"===this._phase?this._renderListening():"captured"===this._phase?this._renderCaptured():"timeout"===this._phase?this._renderTimeout():"duplicate"===this._phase?this._renderDuplicate():this._renderError()}
            </ha-dialog>
        `}};Si.styles=a`
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
    `,e([pe({attribute:!1})],Si.prototype,"api",void 0),e([pe({attribute:!1})],Si.prototype,"hass",void 0),e([pe({attribute:!1})],Si.prototype,"device",void 0),e([pe({attribute:!1})],Si.prototype,"commandName",void 0),e([pe({attribute:!1})],Si.prototype,"timeout",void 0),e([ge()],Si.prototype,"_phase",void 0),e([ge()],Si.prototype,"_result",void 0),e([ge()],Si.prototype,"_duplicate",void 0),e([ge()],Si.prototype,"_error",void 0),e([ge()],Si.prototype,"_timeRemaining",void 0),e([ge()],Si.prototype,"_sessionId",void 0),Si=e([de("ir-capture-dialog")],Si);let Ii=class extends ne{constructor(){super(...arguments),this.title="Confirm",this.message="Are you sure?",this.confirmLabel="Confirm",this.cancelLabel="Cancel",this.destructive=!1,this._busy=!1}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_confirm(){this.dispatchEvent(new CustomEvent("confirmed",{bubbles:!0,composed:!0}))}render(){return j`
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
        `}};Ii.styles=a`
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
            background: #e65100;
            border-color: #e65100;
        }
    `,e([pe()],Ii.prototype,"title",void 0),e([pe()],Ii.prototype,"message",void 0),e([pe()],Ii.prototype,"confirmLabel",void 0),e([pe()],Ii.prototype,"cancelLabel",void 0),e([pe({type:Boolean})],Ii.prototype,"destructive",void 0),e([ge()],Ii.prototype,"_busy",void 0),Ii=e([de("ir-confirm-dialog")],Ii);let Mi=class extends ne{constructor(){super(...arguments),this.value=[],this.disabled=!1,this.excludeEntityIds=[],this._didAutoSelect=!1,this._receiverIds=new Set,this._receiversLoaded=!1}updated(e){if(super.updated(e),e.has("api")&&this.api&&!this._receiversLoaded&&(this._receiversLoaded=!0,this._loadReceivers()),!this._didAutoSelect)if(this.value.length>0)this._didAutoSelect=!0;else{const e=this._getEmitters();1===e.length&&(this._didAutoSelect=!0,this._fireChange([e[0].entity_id]))}}async _loadReceivers(){if(this.api)try{const e=await this.api.listReceivers();this._receiverIds=new Set(e.map(e=>e.entity_id))}catch{this._receiverIds=new Set}}_getEmitters(){const e=this.hass?.states??{},t=new Set(this.excludeEntityIds),i=[];for(const[o,s]of Object.entries(e))!o.startsWith("infrared.")||t.has(o)||this._receiverIds.has(o)||i.push({entity_id:o,name:s.attributes.friendly_name??o});return i}_emitterName(e){const t=this.hass?.states?.[e];return t?.attributes?.friendly_name??e}_onAdd(e){const t=e.target,i=t.value;i&&(t.value="",this.value.includes(i)||this._fireChange([...this.value,i]))}_onRemove(e){this._fireChange(this.value.filter(t=>t!==e))}_fireChange(e){this.value=e,this.dispatchEvent(new CustomEvent("emitters-changed",{detail:{value:e},bubbles:!0,composed:!0}))}render(){const e=this._getEmitters(),t=e.filter(e=>!this.value.includes(e.entity_id));return j`
            <label>IR emitters</label>

            ${this.value.length>0?j`
                      <div class="chips">
                          ${this.value.map(e=>j`
                                  <span class="chip">
                                      <span class="chip-name">${this._emitterName(e)}</span>
                                      ${this.disabled?"":j`<button
                                                class="chip-remove"
                                                @click=${()=>this._onRemove(e)}
                                                title="Remove"
                                            >&times;</button>`}
                                  </span>
                              `)}
                      </div>
                  `:""}

            ${0===e.length?j`<div class="no-emitters">No IR emitters found.</div>`:t.length>0?j`
                        <select
                            @change=${this._onAdd}
                            ?disabled=${this.disabled}
                        >
                            <option value="">+ Add emitter...</option>
                            ${t.map(e=>j`
                                    <option value=${e.entity_id}>
                                        ${e.name}
                                    </option>
                                `)}
                        </select>
                    `:this.value.length>0?j`<div class="all-selected">All emitters selected.</div>`:""}
        `}};Mi.styles=a`
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
    `,e([pe({attribute:!1})],Mi.prototype,"hass",void 0),e([pe({attribute:!1})],Mi.prototype,"api",void 0),e([pe({attribute:!1})],Mi.prototype,"value",void 0),e([pe({type:Boolean})],Mi.prototype,"disabled",void 0),e([pe({attribute:!1})],Mi.prototype,"excludeEntityIds",void 0),e([ge()],Mi.prototype,"_didAutoSelect",void 0),e([ge()],Mi.prototype,"_receiverIds",void 0),Mi=e([de("ir-emitter-picker")],Mi);let Ni=class extends ne{constructor(){super(...arguments),this.signalFingerprint="",this.protocol=null,this.code=null,this.slPattern=null,this.sourceDeviceId=null,this.sourceCommandId=null,this.trigger=null,this._name="",this._minHits=1,this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this.trigger&&(this._name=this.trigger.name,this._minHits=this.trigger.min_hits)}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _save(){const e=this._name.trim();if(e){this._busy=!0,this._error=null;try{let t;if(this.trigger)t=await this.api.updateTrigger(this.trigger.id,{name:e,min_hits:this._minHits});else{const i={name:e,protocol:this.protocol,code:this.code,min_hits:this._minHits,source_device_id:this.sourceDeviceId,source_command_id:this.sourceCommandId};this.signalFingerprint&&(i.signal_fingerprint=this.signalFingerprint),t=await this.api.createTrigger(i)}this.dispatchEvent(new CustomEvent("trigger-saved",{detail:t,bubbles:!0,composed:!0}))}catch(e){this._error=e.message??"Save failed"}finally{this._busy=!1}}else this._error="Name is required."}_emitDelete(){this.trigger&&this.dispatchEvent(new CustomEvent("trigger-delete",{detail:{triggerId:this.trigger.id},bubbles:!0,composed:!0}))}_prontoSlArray(e){const t=e.trim().split(/\s+/);if(t.length<6)return null;const i=parseInt(t[2],16)+parseInt(t[3],16),o=t.slice(4);if(o.length<2*i)return null;const s=[];for(let e=0;e<2*i;e++){const t=parseInt(o[e],16);s.push(t>=48)}return s.length>0?s:null}_renderSignalInfo(){const e=!!this.trigger,t=e?null:this.slPattern;if(t)return j`<span class="diamonds">${[...t].map(e=>"L"===e?j`<span class="diamond long">&#9670;</span>`:j`<span class="diamond short">&#9671;</span>`)}</span>`;const i=e?this.trigger.code:this.code,o=e?this.trigger.protocol:this.protocol;if("PRONTO"===o?.toUpperCase()&&i){const e=this._prontoSlArray(i);if(e)return j`<span class="diamonds">${e.map(e=>e?j`<span class="diamond long">&#9670;</span>`:j`<span class="diamond short">&#9671;</span>`)}</span>`}return j`<span class="proto">Trigger Event</span>`}render(){const e=!!this.trigger;return j`
            <div class="overlay" @click=${this._close}>
                <div class="dialog" @click=${e=>e.stopPropagation()}>
                    <h3 class="heading">
                        ${e?"Edit Trigger":"Create Trigger"}
                    </h3>

                    <!-- Signal info (read-only) -->
                    <div class="signal-info">
                        ${this._renderSignalInfo()}
                    </div>

                    <!-- Name -->
                    <label class="field-label">Trigger Name</label>
                    <input
                        class="field-input"
                        type="text"
                        placeholder="e.g. TV Power"
                        .value=${this._name}
                        @input=${e=>{this._name=e.target.value}}
                        ?disabled=${this._busy}
                    />

                    <!-- Min Hits -->
                    <label class="field-label">
                        Min Hits
                        <span class="field-hint">
                            Number of presses within 5s to fire
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

                    ${this._error?j`<p class="error">${this._error}</p>`:""}

                    <div class="actions">
                        ${e?j`<button
                                  class="btn delete-btn"
                                  @click=${this._emitDelete}
                                  ?disabled=${this._busy}
                              >Delete</button>`:""}
                        <span class="actions-spacer"></span>
                        <button
                            class="btn cancel"
                            @click=${this._close}
                            ?disabled=${this._busy}
                        >Cancel</button>
                        <button
                            class="btn save"
                            @click=${this._save}
                            ?disabled=${this._busy||!this._name.trim()}
                        >${this._busy?"Saving...":e?"Update":"Create"}</button>
                    </div>
                </div>
            </div>
        `}};Ni.styles=a`
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
    `,e([pe({attribute:!1})],Ni.prototype,"api",void 0),e([pe()],Ni.prototype,"signalFingerprint",void 0),e([pe()],Ni.prototype,"protocol",void 0),e([pe()],Ni.prototype,"code",void 0),e([pe()],Ni.prototype,"slPattern",void 0),e([pe()],Ni.prototype,"sourceDeviceId",void 0),e([pe()],Ni.prototype,"sourceCommandId",void 0),e([pe({attribute:!1})],Ni.prototype,"trigger",void 0),e([ge()],Ni.prototype,"_name",void 0),e([ge()],Ni.prototype,"_minHits",void 0),e([ge()],Ni.prototype,"_busy",void 0),e([ge()],Ni.prototype,"_error",void 0),Ni=e([de("ir-trigger-dialog")],Ni);const Pi=[{value:"media_player",label:"Media Player"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"light",label:"Light"},{value:"switch",label:"Switch"},{value:"screen",label:"Screen / Shade"},{value:"other",label:"Other"}];let Hi=class extends ne{constructor(){super(...arguments),this._busy=!1,this._captureName=null,this._toast=null,this._confirmDelete=!1,this._commandToDelete=null,this._actionOptions=[],this._mappingCommandName=null,this._popoverTop=0,this._popoverLeft=0,this._dismissHandler=null,this._editingName=!1,this._draftName="",this._triggers=[],this._triggerCommand=null,this._triggerEdit=null,this._confirmDeleteTriggerId=null,this._sortable=null,this._pendingReorderTimeout=null,this._commandsListVersion=0}_emitterName(e){const t=this.hass?.states?.[e];return t?.attributes?.friendly_name??e}_deviceRegistryName(e){const t=this.hass?.devices?.[e];return t?.name_by_user??t?.name??e}_deviceConfigEntryId(e){const t=this.hass?.devices?.[e];return t?(t.config_entries??[])[0]??null:null}_configEntryDomain(e){const t=this.hass?.config_entries?.entries?.[e];return t?.domain??null}_integrationUrl(e){if(!e)return null;const t=this._configEntryDomain(e);return t?`/config/integrations/integration/${t}`:null}_entityIntegrationUrl(e){const t=e.split(".")[0],i=this.hass?.entities?.[e];return i?.config_entry_id?this._integrationUrl(i.config_entry_id):i?.platform?`/config/integrations/integration/${i.platform}`:`/config/integrations/integration/${t}`}async _refresh(){this.device=await this.api.getDevice(this.device.id),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}_flash(e){this._toast=e,setTimeout(()=>{this._toast=null},2400)}_startEditName(){this._draftName=this.device.name,this._editingName=!0,this.updateComplete.then(()=>{const e=this.shadowRoot?.querySelector(".name-input");e?.focus(),e?.select()})}async _saveName(){const e=this._draftName.trim();if(e&&e!==this.device.name){this._busy=!0;try{this.device=await this.api.updateDevice(this.device.id,{name:e}),this._flash("Name updated"),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Update failed: ${e.message}`)}finally{this._busy=!1,this._editingName=!1}}else this._editingName=!1}_onNameKeyDown(e){"Enter"===e.key?(e.preventDefault(),this._saveName()):"Escape"===e.key&&(this._editingName=!1)}async _onTypeChanged(e){const t=e.target.value;if(t!==this.device.device_type){this._busy=!0;try{this.device=await this.api.updateDevice(this.device.id,{device_type:t}),this._flash("Device type updated"),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Update failed: ${e.message}`)}finally{this._busy=!1}}}async _onEmittersChanged(e){const t=e.detail.value,i=[...this.device.emitter_entity_ids];this.device={...this.device,emitter_entity_ids:t},this._busy=!0;try{this.device=await this.api.updateDevice(this.device.id,{emitter_entity_ids:t}),this._flash("Emitters updated"),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this.device={...this.device,emitter_entity_ids:i},this._flash(`Update failed: ${e.message}`)}finally{this._busy=!1}}connectedCallback(){super.connectedCallback(),this._loadActionOptions(),this._loadTriggers()}updated(e){e.has("device")&&(this._loadActionOptions(),this._loadTriggers()),e.has("_commandsListVersion")&&!this._sortable&&this._attachSortable()}async _loadActionOptions(){try{this._actionOptions=await this.api.getActionOptions(this.device.device_type)}catch{this._actionOptions=[]}}async _loadTriggers(){try{this._triggers=await this.api.listTriggers()}catch{this._triggers=[]}}_commandHasTrigger(e){return this._triggers.some(t=>t.source_command_id===e.id)}_onToggleTrigger(e){const t=e.detail?.command;if(!t)return;const i=this._triggers.find(e=>e.source_command_id===t.id);i?this._triggerEdit=i:this._triggerCommand=t}_closeTriggerDialog(){this._triggerCommand=null,this._triggerEdit=null}async _onTriggerSaved(){this._triggerCommand=null,this._triggerEdit=null,await this._loadTriggers()}_requestDeleteTrigger(e){this._confirmDeleteTriggerId=e}async _doDeleteTrigger(){if(!this._confirmDeleteTriggerId)return;const e=this._confirmDeleteTriggerId;this._confirmDeleteTriggerId=null,this._triggerEdit=null;try{await this.api.deleteTrigger(e),await this._loadTriggers()}catch{}}_getActionLabel(e){const t=this.device.entity_config?.command_mapping??{};for(const[i,o]of Object.entries(t))if(o.toLowerCase()===e.toLowerCase()){const e=this._actionOptions.find(e=>e.key===i);return e?.label??i}return null}_onMapAction(e){const{command:t}=e.detail;if(!t)return;const i=e.target.shadowRoot?.querySelector(".badge-btn");if(i){const e=i.getBoundingClientRect();this._popoverTop=e.bottom+4,this._popoverLeft=Math.max(8,e.right-220)}this._mappingCommandName=t.name,requestAnimationFrame(()=>{this._dismissHandler=e=>{const t=e.composedPath(),i=this.shadowRoot?.querySelector(".action-popover");i&&!t.includes(i)&&this._closePopover()},document.addEventListener("click",this._dismissHandler,!0)})}_closePopover(){this._mappingCommandName=null,this._dismissHandler&&(document.removeEventListener("click",this._dismissHandler,!0),this._dismissHandler=null)}disconnectedCallback(){super.disconnectedCallback(),this._dismissHandler&&(document.removeEventListener("click",this._dismissHandler,!0),this._dismissHandler=null),this._sortable?.destroy(),this._sortable=null,this._cancelPendingReorderSave()}firstUpdated(){this._attachSortable()}_attachSortable(){if(this._sortable)return;const e=this.renderRoot.querySelector(".commands-list");e&&(this._sortable=li.create(e,{handle:".grip-handle",animation:150,ghostClass:"sortable-ghost",onEnd:e=>{const t=e.oldIndex,i=e.newIndex;if(void 0===t||void 0===i||t===i)return;const o=[...this.device.commands],[s]=o.splice(t,1);o.splice(i,0,s),this.device={...this.device,commands:o},this.dispatchEvent(new CustomEvent("commands-reordered",{detail:{commands:o},bubbles:!0,composed:!0})),this._sortable?.destroy(),this._sortable=null;const r=this.renderRoot.querySelector(".commands-list");if(r)for(const e of Array.from(r.querySelectorAll("ir-command-row")))e.remove();this._commandsListVersion++,this._scheduleReorderSave(o.map(e=>e.id))}}))}_scheduleReorderSave(e){this._cancelPendingReorderSave(),this._pendingReorderTimeout=window.setTimeout(async()=>{this._pendingReorderTimeout=null;try{await this.api.reorderCommands(this.device.id,e)}catch(e){this._flash(`Reorder failed: ${e.message}`),await this._refresh()}},500)}_cancelPendingReorderSave(){null!==this._pendingReorderTimeout&&(clearTimeout(this._pendingReorderTimeout),this._pendingReorderTimeout=null)}_getCommandForAction(e){return(this.device.entity_config?.command_mapping??{})[e]??null}async _selectAction(e,t){this._closePopover(),this._busy=!0;try{const i=await this.api.updateMapping(this.device.id,e,t);this.device={...this.device,entity_config:{...this.device.entity_config,command_mapping:i.mapping}},this._flash(t?`Mapped to ${t}`:"Mapping cleared"),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Mapping failed: ${e.message}`)}finally{this._busy=!1}}_getCurrentActionKey(e){const t=this.device.entity_config?.command_mapping??{};for(const[i,o]of Object.entries(t))if(o.toLowerCase()===e.toLowerCase())return i;return""}async _onTest(e){const{command:t}=e.detail;if(t){this._busy=!0;try{await this.api.sendCommand(this.device.id,t.id),this._flash(`Sent "${t.name}"`)}catch(e){this._flash(`Send failed: ${e.message}`)}finally{this._busy=!1}}}_onDelete(e){const{command:t}=e.detail;t&&(this._commandToDelete=t)}async _confirmCommandDelete(){const e=this._commandToDelete;if(e){this._commandToDelete=null,this._cancelPendingReorderSave(),this._busy=!0;try{await this.api.deleteCommand(this.device.id,e.id),await this._refresh(),this._flash(`Removed "${e.name}"`)}catch(e){this._flash(`Delete failed: ${e.message}`)}finally{this._busy=!1}}}_onCaptureClosed(){this._captureName=null}async _onCommandSaved(e){const{commandName:t}=e.detail;this._cancelPendingReorderSave(),await this._refresh(),this._flash(`Saved "${t}"`),this._captureName=null}_goToSniffer(){this.dispatchEvent(new CustomEvent("navigate-sniffer",{bubbles:!0,composed:!0}))}async _deleteDevice(){this._busy=!0;try{await this.api.deleteDevice(this.device.id),this.dispatchEvent(new CustomEvent("device-deleted",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Delete failed: ${e.message}`)}finally{this._busy=!1,this._confirmDelete=!1}}_navigateIntegration(e){e&&(window.history.pushState(null,"",e),window.dispatchEvent(new PopStateEvent("popstate")))}render(){const e=this.device.commands,t=e.length;return j`
            <!-- Header: editable name + delete -->
            <section class="header">
                <div class="header-left">
                    ${this._editingName?j`
                              <input
                                  class="name-input"
                                  type="text"
                                  .value=${this._draftName}
                                  @input=${e=>this._draftName=e.target.value}
                                  @blur=${this._saveName}
                                  @keydown=${this._onNameKeyDown}
                                  ?disabled=${this._busy}
                              />
                          `:j`
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
                <button
                    class="action-btn collapse-btn"
                    @click=${()=>this.dispatchEvent(new CustomEvent("collapse",{bubbles:!0,composed:!0}))}
                    title="Close"
                >&#x2715;</button>
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
                        ${Pi.map(e=>j`
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
                    <span>Commands (${t})</span>
                </div>
                <div class="commands-list">
                    ${ke(this._commandsListVersion,e.length>0?Te(e,e=>e.id,e=>j`
                                      <ir-command-row
                                          data-id=${e.id}
                                          .templateName=${e.name}
                                          .command=${e}
                                          .busy=${this._busy}
                                          .actionLabel=${this._getActionLabel(e.name)}
                                          .hasTrigger=${this._commandHasTrigger(e)}
                                          @map-action=${this._onMapAction}
                                          @test=${this._onTest}
                                          @toggle-trigger=${this._onToggleTrigger}
                                          @delete=${this._onDelete}
                                      >
                                          <ha-svg-icon
                                              slot="status"
                                              class="grip-handle"
                                              .path=${"M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z"}
                                              title="Drag to reorder"
                                          ></ha-svg-icon>
                                      </ir-command-row>
                                  `):j`<div class="empty">No commands yet. Add one below.</div>`)}

                    ${this._mappingCommandName?j`
                              <div
                                  class="action-popover"
                                  style="top:${this._popoverTop}px; left:${this._popoverLeft}px"
                              >
                                  <div class="popover-header">Map action</div>
                                  ${this._getCurrentActionKey(this._mappingCommandName)?j`
                                            <button
                                                class="popover-item clear"
                                                @click=${()=>this._selectAction(this._mappingCommandName,null)}
                                            >
                                                <span class="popover-label">None (clear)</span>
                                            </button>
                                        `:""}
                                  ${this._actionOptions.map(e=>{const t=this._getCurrentActionKey(this._mappingCommandName)===e.key,i=this._getCommandForAction(e.key),o=i&&i.toLowerCase()!==this._mappingCommandName.toLowerCase();return j`
                                          <button
                                              class="popover-item ${t?"active":""}"
                                              @click=${()=>this._selectAction(this._mappingCommandName,e.key)}
                                          >
                                              <span class="popover-label">${e.label}</span>
                                              ${t?j`<span class="popover-check">&#10003;</span>`:o?j`<span class="popover-existing">${i}</span>`:""}
                                          </button>
                                      `})}
                              </div>
                          `:""}
                </div>
            </div>

            <div class="footer-actions">
                <button
                    class="action-btn"
                    @click=${this._goToSniffer}
                    ?disabled=${this._busy}
                >+ Add Command</button>
                <button
                    class="action-btn delete-btn"
                    @click=${()=>this._confirmDelete=!0}
                    ?disabled=${this._busy}
                >Delete Device</button>
            </div>

            <!-- Dialogs -->
            ${this._captureName?j`
                      <ir-capture-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .device=${this.device}
                          .commandName=${this._captureName}
                          @closed=${this._onCaptureClosed}
                          @command-saved=${this._onCommandSaved}
                      ></ir-capture-dialog>
                  `:""}
            ${this._confirmDelete?j`
                      <ir-confirm-dialog
                          title="Delete ${this.device.name}?"
                          message="This removes all captured commands and the auto-created entity. The action cannot be undone."
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._deleteDevice}
                          @closed=${()=>this._confirmDelete=!1}
                      ></ir-confirm-dialog>
                  `:""}
            ${this._commandToDelete?j`
                      <ir-confirm-dialog
                          title="Delete command?"
                          message="Remove &quot;${this._commandToDelete.name}&quot;? This cannot be undone."
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._confirmCommandDelete}
                          @closed=${()=>this._commandToDelete=null}
                      ></ir-confirm-dialog>
                  `:""}
            ${this._triggerCommand?j`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .protocol=${this._triggerCommand.protocol}
                          .code=${this._triggerCommand.code}
                          .sourceDeviceId=${this.device.id}
                          .sourceCommandId=${this._triggerCommand.id}
                          @trigger-saved=${this._onTriggerSaved}
                          @closed=${this._closeTriggerDialog}
                      ></ir-trigger-dialog>
                  `:""}
            ${this._triggerEdit?j`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .trigger=${this._triggerEdit}
                          @trigger-saved=${this._onTriggerSaved}
                          @closed=${this._closeTriggerDialog}
                          @trigger-delete=${e=>this._requestDeleteTrigger(e.detail.triggerId)}
                      ></ir-trigger-dialog>
                  `:""}
            ${this._confirmDeleteTriggerId?j`
                      <ir-confirm-dialog
                          title="Delete Trigger"
                          message="Remove this trigger? The associated HA event entity will also be removed."
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._doDeleteTrigger}
                          @closed=${()=>this._confirmDeleteTriggerId=null}
                      ></ir-confirm-dialog>
                  `:""}
            ${this._toast?j`<div class="toast" role="status">${this._toast}</div>`:""}
        `}};Hi.styles=a`
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
            color: #e65100;
            border-color: rgba(230, 81, 0, 0.25);
        }
        .action-btn.delete-btn:hover {
            background: rgba(230, 81, 0, 0.08);
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
        /* --- Action popover --- */
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
    `,e([pe({attribute:!1})],Hi.prototype,"api",void 0),e([pe({attribute:!1})],Hi.prototype,"hass",void 0),e([pe({attribute:!1})],Hi.prototype,"device",void 0),e([ge()],Hi.prototype,"_busy",void 0),e([ge()],Hi.prototype,"_captureName",void 0),e([ge()],Hi.prototype,"_toast",void 0),e([ge()],Hi.prototype,"_confirmDelete",void 0),e([ge()],Hi.prototype,"_commandToDelete",void 0),e([ge()],Hi.prototype,"_actionOptions",void 0),e([ge()],Hi.prototype,"_mappingCommandName",void 0),e([ge()],Hi.prototype,"_popoverTop",void 0),e([ge()],Hi.prototype,"_popoverLeft",void 0),e([ge()],Hi.prototype,"_editingName",void 0),e([ge()],Hi.prototype,"_draftName",void 0),e([ge()],Hi.prototype,"_triggers",void 0),e([ge()],Hi.prototype,"_triggerCommand",void 0),e([ge()],Hi.prototype,"_triggerEdit",void 0),e([ge()],Hi.prototype,"_confirmDeleteTriggerId",void 0),e([ge()],Hi.prototype,"_commandsListVersion",void 0),Hi=e([de("ir-device-detail")],Hi);let Ri=class extends ne{constructor(){super(...arguments),this.sourceId="",this.sourceName="",this._name="",this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this._name=`${this.sourceName} (Copy)`}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _duplicate(){const e=this._name.trim();if(e){this._busy=!0,this._error=null;try{const t=await this.api.duplicateDevice(this.sourceId,e);this.dispatchEvent(new CustomEvent("device-duplicated",{detail:t,bubbles:!0,composed:!0})),this._close()}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error="Name is required."}_onKeyDown(e){"Enter"===e.key&&(e.preventDefault(),this._duplicate())}render(){return j`
            <ha-dialog
                open
                heading="Duplicate device"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?j`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <p class="hint">
                    Duplicating <strong>${this.sourceName}</strong>. The new
                    device gets a copy of every command, action mapping, and
                    emitter assignment. You can change anything afterward.
                </p>

                <div class="field">
                    <label>Name</label>
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
                        Cancel
                    </button>
                    <button
                        class="action-btn create-btn"
                        @click=${this._duplicate}
                        ?disabled=${this._busy||!this._name.trim()}
                    >
                        ${this._busy?"Duplicating...":"Duplicate"}
                    </button>
                </div>
            </ha-dialog>
        `}};Ri.styles=a`
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
        .dialog-actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            margin-top: 16px;
        }
        .action-btn {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 0.85rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            transition: background 150ms ease, opacity 150ms ease;
        }
        .action-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .cancel-btn {
            color: var(--primary-text-color);
        }
        .cancel-btn:hover:not(:disabled) {
            background: var(--secondary-background-color);
        }
        .create-btn {
            background: #2e7d32;
            color: #fff;
            border-color: #2e7d32;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `,e([pe({attribute:!1})],Ri.prototype,"api",void 0),e([pe({attribute:!1})],Ri.prototype,"sourceId",void 0),e([pe({attribute:!1})],Ri.prototype,"sourceName",void 0),e([ge()],Ri.prototype,"_name",void 0),e([ge()],Ri.prototype,"_busy",void 0),e([ge()],Ri.prototype,"_error",void 0),Ri=e([de("ir-duplicate-device-dialog")],Ri);const Li={media_player:"M21,17H3V5H21M21,3H3A2,2 0 0,0 1,5V17A2,2 0 0,0 3,19H8V21H16V19H21A2,2 0 0,0 23,17V5A2,2 0 0,0 21,3Z",ac:"M11,21H13V11.85L14.6,13.5L16,12.05L12,8L8,12.05L9.4,13.5L11,11.85V21M2,3V11C2,12.66 5.69,14 12,14C18.31,14 22,12.66 22,11V3H2M4,5H20V8.5C18.5,9.27 15.6,10 12,10C8.4,10 5.5,9.27 4,8.5V5Z",fan:"M12,11A1,1 0 0,0 11,12A1,1 0 0,0 12,13A1,1 0 0,0 13,12A1,1 0 0,0 12,11M12.5,2C17,2 17.11,5.57 14.75,6.75C13.76,7.24 13.32,8.29 13.13,9.22C13.61,9.42 14.03,9.73 14.35,10.13C18.05,8.13 22.03,8.92 22.03,12.5C22.03,17 18.46,17.1 17.28,14.73C16.78,13.74 15.72,13.3 14.79,13.11C14.59,13.59 14.28,14 13.88,14.34C15.87,18.03 15.08,22 11.5,22C7,22 6.91,18.42 9.27,17.24C10.25,16.75 10.69,15.71 10.89,14.79C10.4,14.59 9.97,14.27 9.65,13.87C5.96,15.85 2,15.07 2,11.5C2,7 5.56,6.89 6.74,9.26C7.24,10.25 8.29,10.68 9.22,10.87C9.41,10.39 9.73,9.97 10.14,9.65C8.15,5.95 8.94,2 12.5,2Z",light:"M12,2A7,7 0 0,0 5,9C5,11.38 6.19,13.47 8,14.74V17A1,1 0 0,0 9,18H15A1,1 0 0,0 16,17V14.74C17.81,13.47 19,11.38 19,9A7,7 0 0,0 12,2M9,21A1,1 0 0,0 10,22H14A1,1 0 0,0 15,21V20H9V21Z",switch:"M13,3H11V13H13V3M17.83,5.17L16.41,6.59C18,7.35 19,9.05 19,11A7,7 0 0,1 12,18A7,7 0 0,1 5,11C5,9.05 6,7.35 7.58,6.59L6.17,5.17C4.23,6.82 3,9.26 3,12A9,9 0 0,0 12,21A9,9 0 0,0 21,12C21,9.26 19.77,6.82 17.83,5.17Z",screen:"M20,19H4A2,2 0 0,1 2,17V7A2,2 0 0,1 4,5H20A2,2 0 0,1 22,7V17A2,2 0 0,1 20,19M4,7V17H20V7H4M12,10L16,14H13V17H11V14H8L12,10Z",other:"M11,2A2,2 0 0,0 9,4V8H4A2,2 0 0,0 2,10V13A2,2 0 0,0 4,15H5V21A2,2 0 0,0 7,23H17A2,2 0 0,0 19,21V15H20A2,2 0 0,0 22,13V10A2,2 0 0,0 20,8H15V4A2,2 0 0,0 13,2H11Z"},Oi={media_player:"Media Player",ac:"Air Conditioner",fan:"Fan",light:"Light",switch:"Switch",screen:"Screen / Shade",other:"IR Device"},zi="M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19M8,9H16V19H8V9M15.5,4L14.5,3H9.5L8.5,4H5V6H19V4H15.5Z";let Vi=class extends ne{constructor(){super(...arguments),this.devices=[],this.loading=!1,this.expandedDeviceId=null,this._emitters=[],this._captureProviders=[],this._expandedDevice=null,this._triggers=[],this._glowTriggerIds=new Set,this._editTrigger=null,this._confirmDeleteTrigger=null,this._duplicateTarget=null,this._confirmDeleteDevice=null,this._unsubTriggerFired=null}connectedCallback(){super.connectedCallback(),this._discoverHardware(),this._loadTriggers(),this._subscribeTriggerFired()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeTriggerFired()}updated(e){(e.has("hass")||e.has("api"))&&this._discoverHardware(),e.has("api")&&this.api&&!this._unsubTriggerFired&&(this._loadTriggers(),this._subscribeTriggerFired()),e.has("expandedDeviceId")&&this._loadExpandedDevice()}async _loadExpandedDevice(){if(this.expandedDeviceId&&this.api)try{this._expandedDevice=await this.api.getDevice(this.expandedDeviceId)}catch{this._expandedDevice=null}else this._expandedDevice=null}async _onExpandedDeviceChanged(){await this._loadExpandedDevice(),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}_onExpandedDeviceDeleted(){this.dispatchEvent(new CustomEvent("device-deleted",{bubbles:!0,composed:!0}))}_onCommandsReordered(e){if(!this._expandedDevice)return;const t=e.detail?.commands;Array.isArray(t)&&(this._expandedDevice={...this._expandedDevice,commands:t})}_onCollapse(){this.dispatchEvent(new CustomEvent("device-selected",{detail:this.expandedDeviceId,bubbles:!0,composed:!0}))}async _discoverHardware(){const e=new Set;if(this.api)try{const t=await this.api.listReceivers();for(const i of t)e.add(i.entity_id)}catch{}const t=this.hass?.states??{},i=[];for(const[o,s]of Object.entries(t))o.startsWith("infrared.")&&!e.has(o)&&i.push({entity_id:o,name:s.attributes.friendly_name??o});if(this._emitters=i,this.api)try{this._captureProviders=await this.api.listCaptureProviders()}catch{}}_select(e){this.dispatchEvent(new CustomEvent("device-selected",{detail:e,bubbles:!0,composed:!0}))}_add(){this.dispatchEvent(new CustomEvent("add-device",{bubbles:!0,composed:!0}))}_openDuplicateDialog(e,t){t.stopPropagation(),this._duplicateTarget=e}_closeDuplicateDialog(){this._duplicateTarget=null}_onDeviceDuplicated(){this._duplicateTarget=null,this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}_requestDeleteDevice(e,t){t.stopPropagation(),this._confirmDeleteDevice=e}async _doDeleteDevice(){if(!this._confirmDeleteDevice||!this.api)return;const e=this._confirmDeleteDevice;this._confirmDeleteDevice=null;try{await this.api.deleteDevice(e.id),this.dispatchEvent(new CustomEvent("device-deleted",{bubbles:!0,composed:!0}))}catch{}}_navigateIntegration(e){const t=`/config/integrations/integration/${e}`;window.history.pushState(null,"",t),window.dispatchEvent(new PopStateEvent("popstate"))}async _loadTriggers(){if(this.api)try{this._triggers=await this.api.listTriggers()}catch{}}async _subscribeTriggerFired(){if(this.api)try{this._unsubTriggerFired=await this.api.subscribeTriggerFired(e=>{this._glowTriggerIds=new Set([...this._glowTriggerIds,e.trigger_id]),setTimeout(()=>{const t=new Set(this._glowTriggerIds);t.delete(e.trigger_id),this._glowTriggerIds=t},2500)})}catch{}}async _unsubscribeTriggerFired(){this._unsubTriggerFired&&(await this._unsubTriggerFired(),this._unsubTriggerFired=null)}_openEditTrigger(e,t){t.stopPropagation(),this._editTrigger=e}_closeEditTrigger(){this._editTrigger=null}async _onTriggerUpdated(){this._editTrigger=null,await this._loadTriggers()}async _toggleTriggerEnabled(e,t){t.stopPropagation();try{await this.api.updateTrigger(e.id,{enabled:!e.enabled}),await this._loadTriggers()}catch{}}_requestDeleteTrigger(e,t){t.stopPropagation(),this._confirmDeleteTrigger=e}async _doDeleteTrigger(){if(!this._confirmDeleteTrigger)return;const e=this._confirmDeleteTrigger;this._confirmDeleteTrigger=null;try{await this.api.deleteTrigger(e.id),await this._loadTriggers()}catch{}}_emitterIntegrationDomain(e){const t=this.hass?.entities?.[e];return t?.platform?t.platform:e.split(".")[0]}_getEmitterDeviceIds(){const e=new Set;for(const t of this._emitters){const i=this.hass?.entities?.[t.entity_id];i?.device_id&&e.add(i.device_id)}return e}_getEmitterEntityIdsByDevice(){const e=new Map;for(const t of this._emitters){const i=this.hass?.entities?.[t.entity_id],o=i?.device_id;if(!o)continue;const s=e.get(o)??[];s.push(t.entity_id),e.set(o,s)}return e}_isPre2026_6(){const e=this.hass?.config?.version;if(!e)return!1;const t=e.match(/^(\d+)\.(\d+)/);if(!t)return!1;const i=parseInt(t[1],10),o=parseInt(t[2],10);return i<2026||2026===i&&o<6}_resolveNavType(e,t){if("native"===e.type&&t){const e=this.hass?.entities?.[t]?.platform;return e||"esphome"}return e.type}_classifyHardware(){const e=this._getEmitterEntityIdsByDevice(),t=new Set(e.keys()),i=new Map;for(const o of this._captureProviders){let s,r;if("native"===o.type?(r=o.receiver_entity_id??o.device_id,s=this.hass?.entities?.[r]?.device_id,s||(s=r)):s=o.device_id,!s)continue;const a=i.get(s)??{device_id:s,name:o.name,nav_type:this._resolveNavType(o,r),has_native:!1,has_bridge:!1,has_tx:t.has(s),tx_entity_ids:e.get(s)??[]};"native"===o.type?(a.has_native=!0,a.native_entity_id=r):(a.has_bridge=!0,a.name=o.name,a.nav_type=o.type),i.set(s,a)}const o=Array.from(i.values()),s=o.filter(e=>e.has_tx);return{receivers:o,proxies:s}}_renderRxBadges(e){const t=!e.has_native&&e.has_bridge&&this._isPre2026_6();return j`
            ${e.has_native?j`<span
                      class="badge rx-native"
                      title="Receives via HA's native infrared platform"
                  >RX-NATIVE</span>`:X}
            ${e.has_bridge?j`<span
                      class="badge rx-bridge"
                      title=${e.has_native?"Legacy bridge still active. Native receiver supersedes it -- you can remove the on_pronto: block from your ESPHome config.":"Receives via legacy ESPHome event-bus bridge"}
                  >RX-BRIDGE</span>`:X}
            ${t?j`<span
                      class="badge rx-native-disabled"
                      title="Upgrade to HA 2026.6+ for native receiver support"
                  >RX-NATIVE</span>`:X}
        `}render(){if(this.loading)return j`<div class="loading">Loading IR devices...</div>`;const e=this.devices.length>0,t=this._emitters.length>0,{receivers:i,proxies:o}=this._classifyHardware(),s=i.length>0,r=o.length>0,a=this._triggers.length>0;return e||t||s||r?j`
            <!-- Devices -->
            <div class="toolbar">
                <span class="toolbar-title">
                    <ha-svg-icon .path=${"M12,0C8.96,0 6.21,1.23 4.22,3.22L5.63,4.63C7.26,3 9.5,2 12,2C14.5,2 16.74,3 18.36,4.64L19.78,3.22C17.79,1.23 15.04,0 12,0M7.05,6.05L8.46,7.46C9.37,6.56 10.62,6 12,6C13.38,6 14.63,6.56 15.54,7.46L16.95,6.05C15.68,4.78 13.93,4 12,4C10.07,4 8.32,4.78 7.05,6.05M12,15A2,2 0 0,1 10,13A2,2 0 0,1 12,11A2,2 0 0,1 14,13A2,2 0 0,1 12,15M15,9H9A1,1 0 0,0 8,10V22A1,1 0 0,0 9,23H15A1,1 0 0,0 16,22V10A1,1 0 0,0 15,9Z"}></ha-svg-icon>
                    HAIR Devices
                    <span class="toolbar-count">(${this.devices.length})</span>
                </span>
            </div>
            ${e?j`
                      <div class="grid">
                          ${this.devices.map(e=>j`
                                  <div
                                      class="card device-card ${e.id===this.expandedDeviceId?"expanded":""}"
                                      tabindex="0"
                                      @click=${()=>this._select(e.id)}
                                      @keydown=${t=>{"Enter"!==t.key&&" "!==t.key||(t.preventDefault(),this._select(e.id))}}
                                  >
                                      <button
                                          class="card-action duplicate-action"
                                          title="Duplicate device"
                                          @click=${t=>this._openDuplicateDialog(e,t)}
                                      >
                                          <ha-svg-icon .path=${"M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"}></ha-svg-icon>
                                      </button>
                                      <button
                                          class="card-action delete-action"
                                          title="Delete device"
                                          @click=${t=>this._requestDeleteDevice(e,t)}
                                      >
                                          <ha-svg-icon .path=${zi}></ha-svg-icon>
                                      </button>
                                      <div class="card-header">
                                          <ha-svg-icon
                                              .path=${Li[e.device_type]??Li.other}
                                          ></ha-svg-icon>
                                          <div class="card-name">
                                              ${e.name}
                                          </div>
                                      </div>
                                      <div class="card-meta">
                                          ${[e.manufacturer,Oi[e.device_type]].filter(Boolean).join(" • ")}
                                      </div>
                                      <div class="card-footer">
                                          <span class="badge cmd-badge">
                                              CMD: ${e.command_count}
                                          </span>
                                          ${e.emitter_entity_ids.length>0?j`<span class="badge tx-badge">TX: ${e.emitter_entity_ids.length}</span>`:j`<span class="badge no-tx-badge">No TX</span>`}
                                      </div>
                                  </div>
                                  ${e.id===this.expandedDeviceId&&this._expandedDevice?j`
                                            <div class="expanded-detail">
                                                <ir-device-detail
                                                    .api=${this.api}
                                                    .device=${this._expandedDevice}
                                                    .hass=${this.hass}
                                                    @device-changed=${this._onExpandedDeviceChanged}
                                                    @device-deleted=${this._onExpandedDeviceDeleted}
                                                    @commands-reordered=${this._onCommandsReordered}
                                                    @collapse=${this._onCollapse}
                                                ></ir-device-detail>
                                            </div>
                                        `:X}
                              `)}
                      </div>
                  `:j`
                      <div class="empty-devices">
                          No devices yet. Sniff some signals, then add your first device.
                      </div>
                  `}

            <!-- Triggers -->
            ${a?j`
                      <div class="section-header">
                          <h2>Triggers</h2>
                          <span class="section-count">${this._triggers.length}</span>
                      </div>
                      <div class="grid">
                          ${this._triggers.map(e=>j`
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
                                      <div class="card-meta">Trigger Event</div>
                                      <div class="card-footer">
                                          ${e.min_hits>1?j`<span class="badge trigger-hits-badge">
                                                    ${e.min_hits}x hits
                                                </span>`:X}
                                          <span
                                              class="badge trigger-toggle ${e.enabled?"trigger-enabled":"trigger-off"}"
                                              @click=${t=>this._toggleTriggerEnabled(e,t)}
                                          >${e.enabled?"ON":"OFF"}</span>
                                          <ha-svg-icon
                                              class="trigger-trash"
                                              .path=${zi}
                                              title="Delete trigger"
                                              @click=${t=>this._requestDeleteTrigger(e,t)}
                                          ></ha-svg-icon>
                                      </div>
                                  </div>
                              `)}
                      </div>
                  `:X}

            <!-- Emitters -->
            ${t?j`
                      <div class="section-header">
                          <h2>Emitters</h2>
                          <span class="section-count">${this._emitters.length}</span>
                      </div>
                      <div class="grid">
                          ${this._emitters.map(e=>j`
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
                                              title="Sends via HA's native infrared platform"
                                          >TX-NATIVE</span>
                                      </div>
                                  </div>
                              `)}
                      </div>
                  `:X}

            <!-- Receivers (capture-capable hardware; proxies appear here too by design) -->
            ${s?j`
                      <div class="section-header">
                          <h2>Receivers</h2>
                          <span class="section-count">${i.length}</span>
                      </div>
                      <div class="grid">
                          ${i.map(e=>j`
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
                  `:X}

            <!-- Proxies (TX + RX hardware) -->
            ${r?j`
                      <div class="section-header">
                          <h2>Proxies</h2>
                          <span class="section-count">${o.length}</span>
                      </div>
                      <div class="grid">
                          ${o.map(e=>j`
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
                                      ${e.tx_entity_ids[0]?j`<div class="card-meta">${e.tx_entity_ids[0]}</div>`:X}
                                      <div class="card-meta">${e.native_entity_id??e.nav_type}</div>
                                      <div class="card-footer">
                                          <span
                                              class="badge tx-native"
                                              title="Sends via HA's native infrared platform"
                                          >TX-NATIVE</span>
                                          ${this._renderRxBadges(e)}
                                      </div>
                                  </div>
                              `)}
                      </div>
                  `:X}

            ${this._editTrigger?j`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .trigger=${this._editTrigger}
                          @trigger-saved=${this._onTriggerUpdated}
                          @closed=${this._closeEditTrigger}
                      ></ir-trigger-dialog>
                  `:X}

            ${this._confirmDeleteTrigger?j`
                      <ir-confirm-dialog
                          title="Delete Trigger"
                          message="Remove &quot;${this._confirmDeleteTrigger.name}&quot;? The associated HA event entity will also be removed."
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._doDeleteTrigger}
                          @closed=${()=>this._confirmDeleteTrigger=null}
                      ></ir-confirm-dialog>
                  `:X}

            ${this._duplicateTarget&&this.api?j`
                      <ir-duplicate-device-dialog
                          .api=${this.api}
                          .sourceId=${this._duplicateTarget.id}
                          .sourceName=${this._duplicateTarget.name}
                          @device-duplicated=${this._onDeviceDuplicated}
                          @closed=${this._closeDuplicateDialog}
                      ></ir-duplicate-device-dialog>
                  `:X}

            ${this._confirmDeleteDevice?j`
                      <ir-confirm-dialog
                          title="Delete Device"
                          message="Remove &quot;${this._confirmDeleteDevice.name}&quot;? Commands, action mappings, and emitter assignments will be deleted. Triggers are unaffected."
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._doDeleteDevice}
                          @closed=${()=>this._confirmDeleteDevice=null}
                      ></ir-confirm-dialog>
                  `:X}
        `:j`
                <ha-card class="empty">
                    <h2>No IR devices yet</h2>
                    <p>Add your first device to get started.</p>
                    <mwc-button raised @click=${this._add}>+ Add Device</mwc-button>
                </ha-card>
            `}};Vi.styles=a`
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
        .trigger-trash {
            --mdc-icon-size: 16px;
            color: var(--secondary-text-color);
            cursor: pointer;
            margin-left: auto;
            opacity: 0.6;
            transition: color 150ms ease, opacity 150ms ease;
        }
        .trigger-trash:hover {
            color: #e65100;
            opacity: 1;
        }
    `,e([pe({attribute:!1})],Vi.prototype,"devices",void 0),e([pe({attribute:!1})],Vi.prototype,"hass",void 0),e([pe({attribute:!1})],Vi.prototype,"api",void 0),e([pe({type:Boolean})],Vi.prototype,"loading",void 0),e([pe({attribute:!1})],Vi.prototype,"expandedDeviceId",void 0),e([ge()],Vi.prototype,"_emitters",void 0),e([ge()],Vi.prototype,"_captureProviders",void 0),e([ge()],Vi.prototype,"_expandedDevice",void 0),e([ge()],Vi.prototype,"_triggers",void 0),e([ge()],Vi.prototype,"_glowTriggerIds",void 0),e([ge()],Vi.prototype,"_editTrigger",void 0),e([ge()],Vi.prototype,"_confirmDeleteTrigger",void 0),e([ge()],Vi.prototype,"_duplicateTarget",void 0),e([ge()],Vi.prototype,"_confirmDeleteDevice",void 0),Vi=e([de("ir-device-list")],Vi);const Fi=[{value:"media_player",label:"Media Player"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"light",label:"Light"},{value:"switch",label:"Switch"},{value:"screen",label:"Screen / Shade"},{value:"other",label:"Other"}];let Ui=class extends ne{constructor(){super(...arguments),this._name="",this._deviceType="media_player",this._emitterIds=[],this._captureProviders=[],this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this._loadCaptureProviders()}async _loadCaptureProviders(){try{this._captureProviders=await this.api.listCaptureProviders()}catch{}}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _create(){if(this._name.trim())if(0!==this._emitterIds.length){this._busy=!0,this._error=null;try{const e=this._captureProviders[0]??null,t=await this.api.createDevice({name:this._name.trim(),device_type:this._deviceType,emitter_entity_ids:this._emitterIds,capture_device_id:e?.device_id??null,capture_provider_type:e?.type??"esphome"});this.dispatchEvent(new CustomEvent("device-created",{detail:t,bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error="Pick at least one IR emitter.";else this._error="Name is required."}render(){return j`
            <ha-dialog
                open
                heading="Add Device"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?j`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <div class="field">
                    <label>Name</label>
                    <input
                        type="text"
                        .value=${this._name}
                        placeholder="e.g. Living Room TV"
                        required
                        autofocus
                        @input=${e=>this._name=e.target.value}
                    />
                </div>

                <div class="field">
                    <label>Device type</label>
                    <select
                        .value=${this._deviceType}
                        @change=${e=>this._deviceType=e.target.value}
                    >
                        ${Fi.map(e=>j`
                                <option
                                    value=${e.value}
                                    ?selected=${this._deviceType===e.value}
                                >
                                    ${e.label}
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
                        Cancel
                    </button>
                    <button
                        class="action-btn create-btn"
                        @click=${this._create}
                        ?disabled=${this._busy}
                    >
                        ${this._busy?"Creating...":"Create"}
                    </button>
                </div>
            </ha-dialog>
        `}};Ui.styles=a`
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
        ha-alert {
            display: block;
            margin: 8px 0;
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
            border-color: #2e7d32;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `,e([pe({attribute:!1})],Ui.prototype,"api",void 0),e([pe({attribute:!1})],Ui.prototype,"hass",void 0),e([ge()],Ui.prototype,"_name",void 0),e([ge()],Ui.prototype,"_deviceType",void 0),e([ge()],Ui.prototype,"_emitterIds",void 0),e([ge()],Ui.prototype,"_captureProviders",void 0),e([ge()],Ui.prototype,"_busy",void 0),e([ge()],Ui.prototype,"_error",void 0),Ui=e([de("ir-add-device-dialog")],Ui);const ji=[{value:"media_player",label:"Media Player"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"light",label:"Light"},{value:"switch",label:"Switch"},{value:"screen",label:"Screen / Shade"},{value:"other",label:"Other"}];let Bi=class extends ne{constructor(){super(...arguments),this.suggestedDeviceName="",this.initialMode="existing",this._mode="existing",this._devices=[],this._selectedDeviceId="",this._commandName="",this._newName="",this._newType="media_player",this._newEmitterIds=[],this._templates=[],this._customCommand=!1,this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this._mode=this.initialMode,this.suggestedDeviceName&&!this._newName&&(this._newName=this.suggestedDeviceName),this._loadDevices(),"new"===this._mode&&this._loadTemplates(this._newType)}async _loadDevices(){try{if(this._devices=await this.api.listDevices(),this.suggestedDeviceName&&!this._selectedDeviceId){const e=this.suggestedDeviceName.toLowerCase(),t=this._devices.find(t=>t.name.toLowerCase()===e);if(t)return this._selectedDeviceId=t.id,void this._loadTemplates(t.device_type)}if("existing"===this._mode&&this._devices.length>0){const e=this._devices[0];this._loadTemplates(e.device_type)}else"existing"===this._mode&&this._loadTemplates("other")}catch{"existing"===this._mode&&this._loadTemplates("other")}}async _loadTemplates(e){try{this._templates=await this.api.listTemplates(e)}catch{this._templates=[]}this._customCommand||(this._commandName="")}_activeDeviceType(){if("new"===this._mode)return this._newType;const e=this._devices.find(e=>e.id===this._selectedDeviceId);return e?.device_type??"other"}_onDeviceSelected(e){this._selectedDeviceId=e.target.value;const t=this._devices.find(e=>e.id===this._selectedDeviceId);t&&this._loadTemplates(t.device_type)}_onNewTypeChanged(e){this._newType=e.target.value,this._loadTemplates(this._newType)}_switchMode(e){e!==this._mode&&(this._mode=e,this._customCommand=!1,this._commandName="",this._loadTemplates(this._activeDeviceType()))}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _assign(){const e=this._commandName.trim();if(e){this._busy=!0,this._error=null;try{let t;if("existing"===this._mode){if(!this._selectedDeviceId)return this._error="Select a target device.",void(this._busy=!1);t=await this.api.assignSignal({device_id:this.unknownDeviceId,signal_fingerprint:this.signal.fingerprint,hair_device_id:this._selectedDeviceId,command_name:e})}else{if(!this._newName.trim())return this._error="Device name is required.",void(this._busy=!1);if(0===this._newEmitterIds.length)return this._error="Select at least one IR emitter.",void(this._busy=!1);t=await this.api.assignToNewDevice({device_id:this.unknownDeviceId,signal_fingerprint:this.signal.fingerprint,device_name:this._newName.trim(),device_type:this._newType,emitter_entity_ids:this._newEmitterIds,command_name:e})}t.assigned?this.dispatchEvent(new CustomEvent("signal-assigned",{detail:t,bubbles:!0,composed:!0})):this._error="Assignment failed. The signal may have a duplicate code on the target device."}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error="Command name is required."}_fmtTime(e){try{return new Date(e).toLocaleString(void 0,{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return e}}render(){const e=this.signal.protocol??"RAW",t=this.signal.frequency?`${Math.round(this.signal.frequency/1e3)}kHz`:"";return j`
            <ha-dialog
                open
                heading="Assign Signal"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?j`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <div class="signal-header">
                    ${this.suggestedDeviceName?j`<div class="device-name">${this.suggestedDeviceName}</div>`:""}
                    <div class="signal-detail">
                        ${this.signal.sl_pattern?j`<span class="diamonds">${[...this.signal.sl_pattern].map(e=>"L"===e?j`<span class="diamond long">&#9670;</span>`:j`<span class="diamond short">&#9671;</span>`)}</span>`:j`<span class="proto-label">${e}</span>`}
                    </div>
                    <div class="signal-stats">
                        <span>${this.signal.hit_count} hits</span>
                        ${t?j`<span>${t}</span>`:""}
                        <span>${this._fmtTime(this.signal.last_seen)}</span>
                    </div>
                </div>

                <!-- Mode tabs -->
                <div class="mode-tabs">
                    <button
                        class="mode-tab ${"existing"===this._mode?"active":""}"
                        @click=${()=>{this._switchMode("existing")}}
                    >
                        Existing Device
                    </button>
                    <button
                        class="mode-tab ${"new"===this._mode?"active":""}"
                        @click=${()=>{this._switchMode("new")}}
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
        `}_renderExistingMode(){return j`
            <div class="field">
                <label>Target device</label>
                ${0===this._devices.length?j`<ha-alert alert-type="info">
                          No devices yet. Switch to "New Device" to create one.
                      </ha-alert>`:j`
                          <select
                              .value=${this._selectedDeviceId}
                              @change=${this._onDeviceSelected}
                          >
                              <option value="" disabled>Select device...</option>
                              ${this._devices.map(e=>j`
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
        `}_renderNewMode(){return j`
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
                    ${ji.map(e=>j`
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
                .api=${this.api}
                .value=${this._newEmitterIds}
                ?disabled=${this._busy}
                @emitters-changed=${e=>this._newEmitterIds=e.detail.value}
            ></ir-emitter-picker>
        `}_onCommandSelect(e){const t=e.target.value;"__custom__"===t?(this._customCommand=!0,this._commandName="",this.updateComplete.then(()=>{const e=this.shadowRoot?.querySelector(".custom-cmd-input");e?.focus()})):(this._customCommand=!1,this._commandName=t)}_renderCommandPicker(){return this._customCommand?j`
                <div class="field">
                    <label>Command name</label>
                    <div class="custom-cmd-row">
                        <input
                            class="custom-cmd-input"
                            type="text"
                            placeholder="Enter command name"
                            .value=${this._commandName}
                            @input=${e=>this._commandName=e.target.value}
                        />
                        <button
                            class="back-link"
                            @click=${()=>{this._customCommand=!1,this._commandName=""}}
                        >Templates</button>
                    </div>
                </div>
            `:j`
            <div class="field">
                <label>Command name</label>
                <select
                    .value=${this._commandName}
                    @change=${this._onCommandSelect}
                >
                    <option value="" disabled ?selected=${!this._commandName}>
                        Select command...
                    </option>
                    ${this._templates.map(e=>j`
                            <option
                                value=${e.name}
                                ?selected=${this._commandName===e.name}
                            >
                                ${e.name}
                            </option>
                        `)}
                    <option value="__custom__">Custom...</option>
                </select>
            </div>
        `}};Bi.styles=a`
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
    `,e([pe({attribute:!1})],Bi.prototype,"api",void 0),e([pe({attribute:!1})],Bi.prototype,"hass",void 0),e([pe()],Bi.prototype,"unknownDeviceId",void 0),e([pe({attribute:!1})],Bi.prototype,"signal",void 0),e([pe()],Bi.prototype,"suggestedDeviceName",void 0),e([pe()],Bi.prototype,"initialMode",void 0),e([ge()],Bi.prototype,"_mode",void 0),e([ge()],Bi.prototype,"_devices",void 0),e([ge()],Bi.prototype,"_selectedDeviceId",void 0),e([ge()],Bi.prototype,"_commandName",void 0),e([ge()],Bi.prototype,"_newName",void 0),e([ge()],Bi.prototype,"_newType",void 0),e([ge()],Bi.prototype,"_newEmitterIds",void 0),e([ge()],Bi.prototype,"_templates",void 0),e([ge()],Bi.prototype,"_customCommand",void 0),e([ge()],Bi.prototype,"_busy",void 0),e([ge()],Bi.prototype,"_error",void 0),Bi=e([de("ir-assign-signal-dialog")],Bi);const Xi=[{value:"media_player",label:"Media Player"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"light",label:"Light"},{value:"switch",label:"Switch"},{value:"screen",label:"Screen / Shade"},{value:"other",label:"Other"}];let qi=class extends ne{constructor(){super(...arguments),this.suggestedName="",this._name="",this._type="other",this._emitterIds=[],this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this.suggestedName&&!this._name&&(this._name=this.suggestedName)}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _create(){const e=this._name.trim();if(e)if(0!==this._emitterIds.length){this._busy=!0,this._error=null;try{await this.api.createDevice({name:e,device_type:this._type,emitter_entity_ids:this._emitterIds}),this.dispatchEvent(new CustomEvent("device-created",{bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error="Select at least one IR emitter.";else this._error="Device name is required."}render(){return j`
            <ha-dialog
                open
                heading="Promote to Device"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?j`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

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
                        ${Xi.map(e=>j`
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
        `}};qi.styles=a`
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
    `,e([pe({attribute:!1})],qi.prototype,"api",void 0),e([pe({attribute:!1})],qi.prototype,"hass",void 0),e([pe()],qi.prototype,"suggestedName",void 0),e([ge()],qi.prototype,"_name",void 0),e([ge()],qi.prototype,"_type",void 0),e([ge()],qi.prototype,"_emitterIds",void 0),e([ge()],qi.prototype,"_busy",void 0),e([ge()],qi.prototype,"_error",void 0),qi=e([de("ir-promote-dialog")],qi);let Yi=class extends ne{constructor(){super(...arguments),this.value=[],this.busy=!1,this._local=[]}connectedCallback(){super.connectedCallback(),this._local=[...this.value]}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_send(){0!==this._local.length&&this.dispatchEvent(new CustomEvent("send",{detail:{emitters:[...this._local]},bubbles:!0,composed:!0}))}_onEmittersChanged(e){this._local=e.detail.value,this.dispatchEvent(new CustomEvent("emitters-changed",{detail:{value:this._local},bubbles:!0,composed:!0}))}render(){const e=this._local.length>0&&!this.busy;return j`
            <ha-dialog
                open
                heading="Send from"
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
                        Cancel
                    </button>
                    <button
                        class="action-btn send-btn"
                        @click=${this._send}
                        ?disabled=${!e}
                    >
                        ${this.busy?"Sending...":"Send"}
                    </button>
                </div>
            </ha-dialog>
        `}};function Wi(e){try{return new Date(e).toLocaleString(void 0,{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return e}}function Zi(e){try{const t=Date.now()-new Date(e).getTime();return t<6e4?"just now":t<36e5?`${Math.floor(t/6e4)} min ago`:t<864e5?`${Math.floor(t/36e5)}h ago`:`${Math.floor(t/864e5)}d ago`}catch{return""}}Yi.styles=a`
        .dialog-actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            margin-top: 16px;
        }
        .action-btn {
            background: none;
            border: 1px solid var(--divider-color);
            border-radius: 4px;
            padding: 8px 16px;
            font-size: 0.85rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            transition: background 150ms ease, opacity 150ms ease;
        }
        .action-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        .cancel-btn {
            color: var(--primary-text-color);
        }
        .cancel-btn:hover:not(:disabled) {
            background: var(--secondary-background-color);
        }
        .send-btn {
            background: #2e7d32;
            color: #fff;
            border-color: #2e7d32;
        }
        .send-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `,e([pe({attribute:!1})],Yi.prototype,"api",void 0),e([pe({attribute:!1})],Yi.prototype,"hass",void 0),e([pe({attribute:!1})],Yi.prototype,"value",void 0),e([pe({type:Boolean})],Yi.prototype,"busy",void 0),e([ge()],Yi.prototype,"_local",void 0),Yi=e([de("ir-test-emitter-dialog")],Yi);const Ki="M4.93,4.93C3.12,6.74 2,9.24 2,12C2,14.76 3.12,17.26 4.93,19.07L6.34,17.66C4.89,16.22 4,14.22 4,12C4,9.79 4.89,7.78 6.34,6.34L4.93,4.93M19.07,4.93L17.66,6.34C19.11,7.78 20,9.79 20,12C20,14.22 19.11,16.22 17.66,17.66L19.07,19.07C20.88,17.26 22,14.76 22,12C22,9.24 20.88,6.74 19.07,4.93M7.76,7.76C6.67,8.85 6,10.35 6,12C6,13.65 6.67,15.15 7.76,16.24L9.17,14.83C8.45,14.11 8,13.11 8,12C8,10.89 8.45,9.89 9.17,9.17L7.76,7.76M16.24,7.76L14.83,9.17C15.55,9.89 16,10.89 16,12C16,13.11 15.55,14.11 14.83,14.83L16.24,16.24C17.33,15.15 18,13.65 18,12C18,10.35 17.33,8.85 16.24,7.76M12,10A2,2 0 0,0 10,12A2,2 0 0,0 12,14A2,2 0 0,0 14,12A2,2 0 0,0 12,10Z";let Gi=class extends ne{constructor(){super(...arguments),this._devices=[],this._hairDevices=[],this._loading=!0,this._error=null,this._showDismissed=!1,this._expandedId=null,this._expandedDevice=null,this._flashIds=new Set,this._flashStats=new Set,this._recentFingerprints=[],this._glowFingerprints=new Set,this._hitFlashFingerprints=new Set,this._confirmClearAll=!1,this._triggers=[],this._triggerDialog=null,this._triggerEditDialog=null,this._confirmDeleteTriggerId=null,this._editingDeviceId=null,this._editLabel="",this._promoteTarget=null,this._assignSignal=null,this._deleteSignal=null,this._testingFingerprint=null,this._testResult=null,this._testDialog=null,this._testEmitters=[],this._unsubLive=null,this._unsubRemoved=null}connectedCallback(){super.connectedCallback(),this._load(),this._subscribeLive(),this._subscribeRemoved()}updated(e){if(super.updated(e),e.has("_editingDeviceId")&&this._editingDeviceId){const e=this.shadowRoot?.querySelector(".rename-input");e&&(e.focus(),e.select())}}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeLive(),this._unsubscribeRemoved()}async _load(){this._loading=!0;try{const[e,t,i]=await Promise.all([this.api.getUnknownDevices({include_dismissed:this._showDismissed}),this.api.listDevices(),this.api.listTriggers()]);this._devices=e,this._hairDevices=t,this._triggers=i,this._error=null}catch(e){this._error=`Failed to load: ${e.message}`}finally{this._loading=!1}}_matchesHairDevice(e){if(!e)return!1;const t=e.toLowerCase();return this._hairDevices.some(e=>e.name.toLowerCase()===t)}async _subscribeLive(){try{this._unsubLive=await this.api.subscribeUnknownSignals(e=>{this._onLiveSignal(e)})}catch{}}async _unsubscribeLive(){this._unsubLive&&(await this._unsubLive(),this._unsubLive=null)}async _subscribeRemoved(){try{this._unsubRemoved=await this.api.subscribeSignalRemoved(e=>{this._load(),this._expandedId===e.device_id&&(e.device_removed?(this._expandedId=null,this._expandedDevice=null):(this._toggleExpand(e.device_id),this._toggleExpand(e.device_id)))})}catch{}}async _unsubscribeRemoved(){this._unsubRemoved&&(await this._unsubRemoved(),this._unsubRemoved=null)}_startRename(e,t){t.stopPropagation(),this._editingDeviceId=e.id,this._editLabel=e.label??e.protocol??""}async _commitRename(e){const t=this._editLabel.trim();this._editingDeviceId=null;try{const i=await this.api.renameUnknown(e,t),o=this._devices.findIndex(t=>t.id===e);if(o>=0){const e=[...this._devices];e[o]={...e[o],label:i.label},this._devices=e}}catch(e){this._error=`Rename failed: ${e.message}`}}_cancelRename(){this._editingDeviceId=null}_onRenameKeydown(e,t){"Enter"===t.key?this._commitRename(e):"Escape"===t.key&&this._cancelRename()}_promoteDevice(e,t){t.stopPropagation(),this._promoteTarget=e}_closePromote(){this._promoteTarget=null}async _onDevicePromoted(){this._promoteTarget=null,await this._load()}_openAssign(e,t,i,o){this._assignSignal={deviceId:e,signal:t,label:i??null,initialMode:o??"existing"}}_closeAssign(){this._assignSignal=null}async _onSignalAssigned(e){if(this._assignSignal=null,await this._load(),this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{this._expandedId=null,this._expandedDevice=null}}_openDelete(e,t){this._deleteSignal={deviceId:e,signal:t}}_closeDelete(){this._deleteSignal=null}async _confirmDelete(){if(!this._deleteSignal)return;const{deviceId:e,signal:t}=this._deleteSignal;this._deleteSignal=null;try{await this.api.deleteSignal(e,t.fingerprint),await this._load()}catch(e){this._error=`Delete failed: ${e.message}`}}_openTestDialog(e){this._testDialog={signal:e}}_closeTestDialog(){this._testDialog=null}async _sendTest(e){if(!this._testDialog)return;const{signal:t}=this._testDialog,i=e.detail.emitters;if(0!==i.length){this._testingFingerprint=t.fingerprint,this._testResult=null,this._testDialog=null;try{const e=(await Promise.allSettled(i.map(e=>this.api.testSignal(t.fingerprint,e)))).filter(e=>"fulfilled"===e.status&&e.value.sent).length,o=i.length;this._testResult=e===o?1===o?"Sent!":`Sent! (${e}/${o})`:0===e?"Failed":`Sent (${e}/${o})`}catch{this._testResult="Error"}setTimeout(()=>{this._testResult=null,this._testingFingerprint=null},3e3)}}_hasTrigger(e){return this._triggers.some(t=>t.signal_fingerprint===e)}_openTriggerDialog(e,t){const i=this._triggers.find(e=>e.signal_fingerprint===t.fingerprint);i?this._triggerEditDialog=i:this._triggerDialog={signal:t,deviceId:e}}_closeTriggerDialog(){this._triggerDialog=null,this._triggerEditDialog=null}_requestDeleteTrigger(e){this._confirmDeleteTriggerId=e}async _doDeleteTrigger(){if(!this._confirmDeleteTriggerId)return;const e=this._confirmDeleteTriggerId;this._confirmDeleteTriggerId=null,this._triggerEditDialog=null;try{await this.api.deleteTrigger(e),this._triggers=await this.api.listTriggers()}catch{}}async _onTriggerSaved(){this._triggerDialog=null,this._triggerEditDialog=null;try{this._triggers=await this.api.listTriggers()}catch{}}_onLiveSignal(e){const t=(new Date).toISOString(),i=this._devices.findIndex(t=>t.id===e.device_id);if(i>=0){{const o={...this._devices[i]};o.hit_count=e.device_hit_count??e.hit_count,o.last_seen=t,1===e.hit_count&&(o.signal_count=(o.signal_count??0)+1);const s=[...this._devices];s[i]=o,this._devices=s}if(this._expandedDevice&&this._expandedId===e.device_id){const i=this._expandedDevice.signals.findIndex(t=>t.fingerprint===e.signal_fingerprint);if(i>=0){const o={...this._expandedDevice.signals[i]};o.hit_count=e.hit_count,o.last_seen=t;const s=[...this._expandedDevice.signals];s[i]=o,this._expandedDevice={...this._expandedDevice,hit_count:e.device_hit_count??e.hit_count,last_seen:t,signals:s}}else this.api.getUnknownDevice(e.device_id).then(t=>{if(this._expandedId===e.device_id){this._expandedDevice=t;const i=this._devices.findIndex(t=>t.id===e.device_id);if(i>=0){const e={...this._devices[i],signal_count:t.signals.length},o=[...this._devices];o[i]=e,this._devices=o}}}).catch(()=>{})}if(this._flashIds=new Set([...this._flashIds,e.device_id]),setTimeout(()=>{const t=new Set(this._flashIds);t.delete(e.device_id),this._flashIds=t},800),this._flashStats=new Set([...this._flashStats,e.device_id]),setTimeout(()=>{const t=new Set(this._flashStats);t.delete(e.device_id),this._flashStats=t},1500),e.signal_fingerprint){const t=[e.signal_fingerprint,...this._recentFingerprints.filter(t=>t!==e.signal_fingerprint)].slice(0,2);this._recentFingerprints=t,this._glowFingerprints=new Set([...this._glowFingerprints,e.signal_fingerprint]),setTimeout(()=>{const t=new Set(this._glowFingerprints);t.delete(e.signal_fingerprint),this._glowFingerprints=t},1200),this._hitFlashFingerprints=new Set([...this._hitFlashFingerprints,e.signal_fingerprint]),setTimeout(()=>{const t=new Set(this._hitFlashFingerprints);t.delete(e.signal_fingerprint),this._hitFlashFingerprints=t},1200)}}else this._load()}async _toggleExpand(e){if(this._expandedId===e)return this._expandedId=null,void(this._expandedDevice=null);this._expandedId=e;try{this._expandedDevice=await this.api.getUnknownDevice(e)}catch{this._expandedDevice=null}}async _dismiss(e){try{await this.api.dismissUnknown(e),await this._load(),this._expandedId===e&&(this._expandedId=null,this._expandedDevice=null)}catch(e){this._error=`Dismiss failed: ${e.message}`}}async _undismiss(e){try{await this.api.undismissUnknown(e),await this._load()}catch(e){this._error=`Restore failed: ${e.message}`}}async _doClearAll(){this._confirmClearAll=!1;try{await this.api.clearUnknowns(),this._devices=[],this._expandedId=null,this._expandedDevice=null}catch(e){this._error=`Clear failed: ${e.message}`}}_toggleDismissed(){this._showDismissed=!this._showDismissed,this._load()}render(){return j`
            <div class="toolbar">
                <span class="title">
                    <ha-svg-icon .path=${Ki}></ha-svg-icon>
                    HAIR Sniffer
                    ${this._loading?"":j`<span class="count">(${this._devices.length})</span>`}
                </span>
                <div class="toolbar-actions">
                    <button
                        class="action-btn dismiss-btn"
                        @click=${this._toggleDismissed}
                    >${this._showDismissed?"Hide Dismissed":"Show Dismissed"}</button>
                    ${this._devices.length>0?j`
                              <button
                                  class="action-btn delete-btn"
                                  @click=${()=>this._confirmClearAll=!0}
                              >Clear All</button>
                          `:""}
                </div>
            </div>

            ${this._error?j`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

            ${this._loading?j`<div class="loading">Scanning for signals...</div>`:0===this._devices.length?j`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${Ki}></ha-svg-icon>
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
                    `:j`
                        <div class="device-list">
                            ${this._devices.map(e=>this._renderDevice(e))}
                        </div>
                    `}

            ${this._assignSignal?j`
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

            ${this._promoteTarget?j`
                      <ir-promote-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .suggestedName=${this._promoteTarget.label??""}
                          @device-created=${this._onDevicePromoted}
                          @closed=${this._closePromote}
                      ></ir-promote-dialog>
                  `:""}

            ${this._deleteSignal?j`
                      <ir-confirm-dialog
                          title="Delete Signal"
                          message="Remove this signal permanently? This cannot be undone."
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._confirmDelete}
                          @closed=${this._closeDelete}
                      ></ir-confirm-dialog>
                  `:""}

            ${this._confirmClearAll?j`
                      <ir-confirm-dialog
                          title="Clear All Signals"
                          message="Remove all unknown signals and devices? This cannot be undone."
                          confirmLabel="Clear All"
                          .destructive=${!0}
                          @confirmed=${this._doClearAll}
                          @closed=${()=>this._confirmClearAll=!1}
                      ></ir-confirm-dialog>
                  `:""}

            ${this._triggerDialog?j`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .signalFingerprint=${this._triggerDialog.signal.fingerprint}
                          .protocol=${this._triggerDialog.signal.protocol}
                          .code=${this._triggerDialog.signal.code}
                          .slPattern=${this._triggerDialog.signal.sl_pattern??null}
                          @trigger-saved=${this._onTriggerSaved}
                          @closed=${this._closeTriggerDialog}
                      ></ir-trigger-dialog>
                  `:""}
            ${this._testDialog?j`
                      <ir-test-emitter-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .value=${this._testEmitters}
                          @emitters-changed=${e=>this._testEmitters=e.detail.value}
                          @send=${this._sendTest}
                          @closed=${this._closeTestDialog}
                      ></ir-test-emitter-dialog>
                  `:""}
            ${this._triggerEditDialog?j`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .trigger=${this._triggerEditDialog}
                          @trigger-saved=${this._onTriggerSaved}
                          @closed=${this._closeTriggerDialog}
                          @trigger-delete=${e=>this._requestDeleteTrigger(e.detail.triggerId)}
                      ></ir-trigger-dialog>
                  `:""}
            ${this._confirmDeleteTriggerId?j`
                      <ir-confirm-dialog
                          title="Delete Trigger"
                          message="Remove this trigger? The associated HA event entity will also be removed."
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._doDeleteTrigger}
                          @closed=${()=>this._confirmDeleteTriggerId=null}
                      ></ir-confirm-dialog>
                  `:""}
        `}_renderDevice(e){const t=this._expandedId===e.id,i=this._flashIds.has(e.id),o=this._flashStats.has(e.id);return j`
            <ha-card class="device ${i?"flash":""} ${e.dismissed?"dismissed":""}">
                <div
                    class="device-row"
                    @click=${()=>this._toggleExpand(e.id)}
                >
                    <div class="device-info">
                        <div class="device-header">
                            ${this._editingDeviceId===e.id?j`<input
                                      class="rename-input"
                                      type="text"
                                      .value=${this._editLabel}
                                      @input=${e=>{this._editLabel=e.target.value}}
                                      @keydown=${t=>this._onRenameKeydown(e.id,t)}
                                      @blur=${()=>{this._commitRename(e.id)}}
                                      @click=${e=>e.stopPropagation()}
                                  />`:j`<span
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
                            ${e.device_address?j`<span class="address">addr: ${e.device_address}</span>`:""}
                            ${e.dismissed?j`<span class="dismissed-badge">dismissed</span>`:""}
                        </div>
                        <div class="device-stats ${o?"stats-flash":""}">
                            <span class="stat">
                                <strong>${e.hit_count}</strong> hits
                            </span>
                            <span class="stat">
                                <strong>${e.signal_count}</strong> signals
                            </span>
                            <span class="stat last-seen" title=${Wi(e.last_seen)}>
                                ${Zi(e.last_seen)}
                            </span>
                            ${e.label&&this._matchesHairDevice(e.label)?j`<span
                                      class="status-badge hair-device"
                                      @click=${e=>e.stopPropagation()}
                                  >HAIR Device</span>`:e.label?j`<span
                                          class="status-badge promote-badge"
                                          @click=${t=>this._promoteDevice(e,t)}
                                      >Promote</span>`:""}
                        </div>
                    </div>
                    ${e.dismissed?j`<button
                              class="action-btn device-dismiss-btn"
                              @click=${t=>{t.stopPropagation(),this._undismiss(e.id)}}
                          >Restore</button>`:j`<button
                              class="action-btn device-dismiss-btn"
                              @click=${t=>{t.stopPropagation(),this._dismiss(e.id)}}
                          >Dismiss</button>`}
                    <ha-svg-icon
                        class="expand-icon"
                        .path=${t?"M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z":"M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z"}
                    ></ha-svg-icon>
                </div>

                ${t&&this._expandedDevice?this._renderExpanded(this._expandedDevice):""}
            </ha-card>
        `}_renderExpanded(e){return j`
            <div class="expanded">
                <div class="signal-header">
                    <span>Signals (${e.signals.length})</span>
                    <span class="first-seen">First seen: ${Wi(e.first_seen)}</span>
                </div>
                <div class="signal-list">
                    ${e.signals.map(t=>{const i=this._recentFingerprints.indexOf(t.fingerprint),o=0===i,s=1===i,r=this._glowFingerprints.has(t.fingerprint),a=this._hitFlashFingerprints.has(t.fingerprint);return j`
                            <div class="signal-row">
                                <div class="signal-info">
                                    ${t.sl_pattern?j`<span class="diamonds">${[...t.sl_pattern].map(e=>"L"===e?j`<span class="diamond long">◆</span>`:j`<span class="diamond short">◇</span>`)}</span>`:j`<span class="signal-short-label">IR Signal</span>`}
                                </div>
                                <div class="signal-meta">
                                    <span class="${a?"hit-flash":""}">${t.hit_count} hits</span>
                                    <span title=${Wi(t.last_seen)}
                                        >${Zi(t.last_seen)}</span
                                    >
                                </div>
                                <div class="signal-actions">
                                    <button
                                        class="action-btn assign-btn ${o?"recent-latest":""} ${s?"recent-previous":""} ${r?"glow":""}"
                                        @click=${i=>{i.stopPropagation(),this._openAssign(e.id,t,e.label)}}
                                    >Assign</button>
                                    <button
                                        class="action-btn test-btn"
                                        @click=${e=>{e.stopPropagation(),this._openTestDialog(t)}}
                                        ?disabled=${this._testingFingerprint===t.fingerprint}
                                    >${this._testingFingerprint===t.fingerprint?this._testResult??"Sending...":"Test"}</button>
                                    <button
                                        class="action-btn trigger-btn ${this._hasTrigger(t.fingerprint)?"trigger-on":""}"
                                        @click=${i=>{i.stopPropagation(),this._openTriggerDialog(e.id,t)}}
                                    >Trigger</button>
                                    <button
                                        class="action-btn delete-btn"
                                        @click=${i=>{i.stopPropagation(),this._openDelete(e.id,t)}}
                                    >Delete</button>
                                </div>
                            </div>
                        `})}
                </div>
            </div>
        `}};Gi.styles=a`
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
            font-size: 0.7rem;
            font-weight: 500;
            font-family: inherit;
            padding: 2px 8px;
            border-radius: 4px;
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
            background: rgba(0, 150, 136, 0.15);
            color: #00897b;
            border: 1px solid rgba(0, 150, 136, 0.3);
            margin-left: 4px;
            cursor: pointer;
            transition: background 150ms ease;
        }
        .status-badge.promote-badge:hover {
            background: rgba(0, 150, 136, 0.25);
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
        .action-btn.trigger-btn {
            color: #b89930;
            border-color: rgba(184, 153, 48, 0.3);
        }
        .action-btn.trigger-btn:hover {
            background: rgba(184, 153, 48, 0.08);
        }
        .action-btn.trigger-btn.trigger-on {
            color: #fff;
            background: #b89930;
            border-color: #b89930;
        }
        .action-btn.trigger-btn.trigger-on:hover {
            background: #a08328;
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
    `,e([pe({attribute:!1})],Gi.prototype,"api",void 0),e([pe({attribute:!1})],Gi.prototype,"hass",void 0),e([ge()],Gi.prototype,"_devices",void 0),e([ge()],Gi.prototype,"_hairDevices",void 0),e([ge()],Gi.prototype,"_loading",void 0),e([ge()],Gi.prototype,"_error",void 0),e([ge()],Gi.prototype,"_showDismissed",void 0),e([ge()],Gi.prototype,"_expandedId",void 0),e([ge()],Gi.prototype,"_expandedDevice",void 0),e([ge()],Gi.prototype,"_flashIds",void 0),e([ge()],Gi.prototype,"_flashStats",void 0),e([ge()],Gi.prototype,"_recentFingerprints",void 0),e([ge()],Gi.prototype,"_glowFingerprints",void 0),e([ge()],Gi.prototype,"_hitFlashFingerprints",void 0),e([ge()],Gi.prototype,"_confirmClearAll",void 0),e([ge()],Gi.prototype,"_triggers",void 0),e([ge()],Gi.prototype,"_triggerDialog",void 0),e([ge()],Gi.prototype,"_triggerEditDialog",void 0),e([ge()],Gi.prototype,"_confirmDeleteTriggerId",void 0),e([ge()],Gi.prototype,"_editingDeviceId",void 0),e([ge()],Gi.prototype,"_editLabel",void 0),e([ge()],Gi.prototype,"_promoteTarget",void 0),e([ge()],Gi.prototype,"_assignSignal",void 0),e([ge()],Gi.prototype,"_deleteSignal",void 0),e([ge()],Gi.prototype,"_testingFingerprint",void 0),e([ge()],Gi.prototype,"_testResult",void 0),e([ge()],Gi.prototype,"_testDialog",void 0),e([ge()],Gi.prototype,"_testEmitters",void 0),Gi=e([de("ir-signal-monitor")],Gi);let Ji=class extends ne{constructor(){super(...arguments),this.narrow=!1,this._activeTab="devices",this._devices=[],this._expandedDeviceId=null,this._loading=!0,this._error=null,this._addDialogOpen=!1,this._api=null}connectedCallback(){super.connectedCallback(),this.hass&&this._init()}updated(e){e.has("hass")&&this.hass&&!this._api&&this._init()}_init(){this._api=new ue(this.hass),this._refreshDevices()}async _refreshDevices(){if(this._api){this._loading=!0;try{this._devices=await this._api.listDevices(),this._error=null}catch(e){this._error=`Failed to load devices: ${e.message}`}finally{this._loading=!1}}}_toggleDevice(e){this._expandedDeviceId=this._expandedDeviceId===e?null:e}_openAddDialog(){this._addDialogOpen=!0}_closeAddDialog(){this._addDialogOpen=!1}async _onDeviceCreated(e){this._addDialogOpen=!1,await this._refreshDevices(),this._expandedDeviceId=e.detail.id}async _onDeviceChanged(){await this._refreshDevices()}async _onDeviceDeleted(){this._expandedDeviceId=null,await this._refreshDevices()}_switchTab(e){this._expandedDeviceId=null,this._activeTab=e,"devices"===e&&this._refreshDevices()}render(){return this._api?j`
            <ha-top-app-bar-fixed>
                <ha-menu-button
                    slot="navigationIcon"
                    .hass=${this.hass}
                ></ha-menu-button>
                <span slot="title">Home Assistant Infrared Registry</span>
            </ha-top-app-bar-fixed>

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
                    Devices
                </button>
                <button
                    class="tab ${"sniffer"===this._activeTab?"active":""}"
                    @click=${()=>this._switchTab("sniffer")}
                >
                    Sniffer
                </button>
                <div class="tab-spacer"></div>
                ${"devices"===this._activeTab?j`
                          <button
                              class="add-device-btn"
                              @click=${this._openAddDialog}
                          >
                              <ha-svg-icon
                                  .path=${"M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z"}
                              ></ha-svg-icon>
                              Add Device
                          </button>
                      `:""}
            </div>

            <div class="content">
                ${this._error?j`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}
                ${"devices"===this._activeTab?j`
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

                      `:j`
                          <ir-signal-monitor
                              .api=${this._api}
                              .hass=${this.hass}
                          ></ir-signal-monitor>
                      `}
            </div>

            ${this._addDialogOpen?j`
                      <ir-add-device-dialog
                          .api=${this._api}
                          .hass=${this.hass}
                          @closed=${this._closeAddDialog}
                          @device-created=${this._onDeviceCreated}
                      ></ir-add-device-dialog>
                  `:""}
        `:j`<div class="loading">Loading…</div>`}};Ji.styles=a`
        :host {
            display: block;
            background: var(--primary-background-color);
            color: var(--primary-text-color);
            min-height: 100vh;
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
    `,e([pe({attribute:!1})],Ji.prototype,"hass",void 0),e([pe({attribute:!1})],Ji.prototype,"narrow",void 0),e([pe({attribute:!1})],Ji.prototype,"route",void 0),e([pe({attribute:!1})],Ji.prototype,"panel",void 0),e([ge()],Ji.prototype,"_activeTab",void 0),e([ge()],Ji.prototype,"_devices",void 0),e([ge()],Ji.prototype,"_expandedDeviceId",void 0),e([ge()],Ji.prototype,"_loading",void 0),e([ge()],Ji.prototype,"_error",void 0),e([ge()],Ji.prototype,"_addDialogOpen",void 0),Ji=e([de("ha-panel-ir-devices")],Ji);export{Ji as HaPanelIrDevices};
