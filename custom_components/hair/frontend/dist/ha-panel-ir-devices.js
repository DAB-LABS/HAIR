function e(e,t,i,s){var o,a=arguments.length,r=a<3?t:null===s?s=Object.getOwnPropertyDescriptor(t,i):s;if("object"==typeof Reflect&&"function"==typeof Reflect.decorate)r=Reflect.decorate(e,t,i,s);else for(var n=e.length-1;n>=0;n--)(o=e[n])&&(r=(a<3?o(r):a>3?o(t,i,r):o(t,i))||r);return a>3&&r&&Object.defineProperty(t,i,r),r}"function"==typeof SuppressedError&&SuppressedError;const t=globalThis,i=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,s=Symbol(),o=new WeakMap;let a=class{constructor(e,t,i){if(this._$cssResult$=!0,i!==s)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(i&&void 0===e){const i=void 0!==t&&1===t.length;i&&(e=o.get(t)),void 0===e&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),i&&o.set(t,e))}return e}toString(){return this.cssText}};const r=(e,...t)=>{const i=1===e.length?e[0]:t.reduce((t,i,s)=>t+(e=>{if(!0===e._$cssResult$)return e.cssText;if("number"==typeof e)return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(i)+e[s+1],e[0]);return new a(i,e,s)},n=i?e=>e:e=>e instanceof CSSStyleSheet?(e=>{let t="";for(const i of e.cssRules)t+=i.cssText;return(e=>new a("string"==typeof e?e:e+"",void 0,s))(t)})(e):e,{is:l,defineProperty:d,getOwnPropertyDescriptor:c,getOwnPropertyNames:h,getOwnPropertySymbols:p,getPrototypeOf:g}=Object,u=globalThis,m=u.trustedTypes,v=m?m.emptyScript:"",_=u.reactiveElementPolyfillSupport,b=(e,t)=>e,f={toAttribute(e,t){switch(t){case Boolean:e=e?v:null;break;case Object:case Array:e=null==e?e:JSON.stringify(e)}return e},fromAttribute(e,t){let i=e;switch(t){case Boolean:i=null!==e;break;case Number:i=null===e?null:Number(e);break;case Object:case Array:try{i=JSON.parse(e)}catch(e){i=null}}return i}},y=(e,t)=>!l(e,t),x={attribute:!0,type:String,converter:f,reflect:!1,useDefault:!1,hasChanged:y};Symbol.metadata??=Symbol("metadata"),u.litPropertyMetadata??=new WeakMap;let $=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??=[]).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=x){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const i=Symbol(),s=this.getPropertyDescriptor(e,i,t);void 0!==s&&d(this.prototype,e,s)}}static getPropertyDescriptor(e,t,i){const{get:s,set:o}=c(this.prototype,e)??{get(){return this[t]},set(e){this[t]=e}};return{get:s,set(t){const a=s?.call(this);o?.call(this,t),this.requestUpdate(e,a,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??x}static _$Ei(){if(this.hasOwnProperty(b("elementProperties")))return;const e=g(this);e.finalize(),void 0!==e.l&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(b("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(b("properties"))){const e=this.properties,t=[...h(e),...p(e)];for(const i of t)this.createProperty(i,e[i])}const e=this[Symbol.metadata];if(null!==e){const t=litPropertyMetadata.get(e);if(void 0!==t)for(const[e,i]of t)this.elementProperties.set(e,i)}this._$Eh=new Map;for(const[e,t]of this.elementProperties){const i=this._$Eu(e,t);void 0!==i&&this._$Eh.set(i,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const i=new Set(e.flat(1/0).reverse());for(const e of i)t.unshift(n(e))}else void 0!==e&&t.push(n(e));return t}static _$Eu(e,t){const i=t.attribute;return!1===i?void 0:"string"==typeof i?i:"string"==typeof e?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(e=>this.enableUpdating=e),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(e=>e(this))}addController(e){(this._$EO??=new Set).add(e),void 0!==this.renderRoot&&this.isConnected&&e.hostConnected?.()}removeController(e){this._$EO?.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const i of t.keys())this.hasOwnProperty(i)&&(e.set(i,this[i]),delete this[i]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((e,s)=>{if(i)e.adoptedStyleSheets=s.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(const i of s){const s=document.createElement("style"),o=t.litNonce;void 0!==o&&s.setAttribute("nonce",o),s.textContent=i.cssText,e.appendChild(s)}})(e,this.constructor.elementStyles),e}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(e=>e.hostConnected?.())}enableUpdating(e){}disconnectedCallback(){this._$EO?.forEach(e=>e.hostDisconnected?.())}attributeChangedCallback(e,t,i){this._$AK(e,i)}_$ET(e,t){const i=this.constructor.elementProperties.get(e),s=this.constructor._$Eu(e,i);if(void 0!==s&&!0===i.reflect){const o=(void 0!==i.converter?.toAttribute?i.converter:f).toAttribute(t,i.type);this._$Em=e,null==o?this.removeAttribute(s):this.setAttribute(s,o),this._$Em=null}}_$AK(e,t){const i=this.constructor,s=i._$Eh.get(e);if(void 0!==s&&this._$Em!==s){const e=i.getPropertyOptions(s),o="function"==typeof e.converter?{fromAttribute:e.converter}:void 0!==e.converter?.fromAttribute?e.converter:f;this._$Em=s;const a=o.fromAttribute(t,e.type);this[s]=a??this._$Ej?.get(s)??a,this._$Em=null}}requestUpdate(e,t,i,s=!1,o){if(void 0!==e){const a=this.constructor;if(!1===s&&(o=this[e]),i??=a.getPropertyOptions(e),!((i.hasChanged??y)(o,t)||i.useDefault&&i.reflect&&o===this._$Ej?.get(e)&&!this.hasAttribute(a._$Eu(e,i))))return;this.C(e,t,i)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(e,t,{useDefault:i,reflect:s,wrapped:o},a){i&&!(this._$Ej??=new Map).has(e)&&(this._$Ej.set(e,a??t??this[e]),!0!==o||void 0!==a)||(this._$AL.has(e)||(this.hasUpdated||i||(t=void 0),this._$AL.set(e,t)),!0===s&&this._$Em!==e&&(this._$Eq??=new Set).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}const e=this.scheduleUpdate();return null!=e&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[e,t]of this._$Ep)this[e]=t;this._$Ep=void 0}const e=this.constructor.elementProperties;if(e.size>0)for(const[t,i]of e){const{wrapped:e}=i,s=this[t];!0!==e||this._$AL.has(t)||void 0===s||this.C(t,void 0,i,s)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),this._$EO?.forEach(e=>e.hostUpdate?.()),this.update(t)):this._$EM()}catch(t){throw e=!1,this._$EM(),t}e&&this._$AE(t)}willUpdate(e){}_$AE(e){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(e){}firstUpdated(e){}};$.elementStyles=[],$.shadowRootOptions={mode:"open"},$[b("elementProperties")]=new Map,$[b("finalized")]=new Map,_?.({ReactiveElement:$}),(u.reactiveElementVersions??=[]).push("2.1.2");const w=globalThis,k=e=>e,D=w.trustedTypes,S=D?D.createPolicy("lit-html",{createHTML:e=>e}):void 0,C="$lit$",T=`lit$${Math.random().toFixed(9).slice(2)}$`,A="?"+T,E=`<${A}>`,P=document,I=()=>P.createComment(""),R=e=>null===e||"object"!=typeof e&&"function"!=typeof e,M=Array.isArray,H="[ \t\n\f\r]",N=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,z=/-->/g,L=/>/g,V=RegExp(`>|${H}(?:([^\\s"'>=/]+)(${H}*=${H}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),O=/'/g,U=/"/g,F=/^(?:script|style|textarea|title)$/i,B=(e,...t)=>({_$litType$:1,strings:e,values:t}),j=Symbol.for("lit-noChange"),q=Symbol.for("lit-nothing"),X=new WeakMap,Z=P.createTreeWalker(P,129);function Y(e,t){if(!M(e)||!e.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==S?S.createHTML(t):t}class W{constructor({strings:e,_$litType$:t},i){let s;this.parts=[];let o=0,a=0;const r=e.length-1,n=this.parts,[l,d]=((e,t)=>{const i=e.length-1,s=[];let o,a=2===t?"<svg>":3===t?"<math>":"",r=N;for(let t=0;t<i;t++){const i=e[t];let n,l,d=-1,c=0;for(;c<i.length&&(r.lastIndex=c,l=r.exec(i),null!==l);)c=r.lastIndex,r===N?"!--"===l[1]?r=z:void 0!==l[1]?r=L:void 0!==l[2]?(F.test(l[2])&&(o=RegExp("</"+l[2],"g")),r=V):void 0!==l[3]&&(r=V):r===V?">"===l[0]?(r=o??N,d=-1):void 0===l[1]?d=-2:(d=r.lastIndex-l[2].length,n=l[1],r=void 0===l[3]?V:'"'===l[3]?U:O):r===U||r===O?r=V:r===z||r===L?r=N:(r=V,o=void 0);const h=r===V&&e[t+1].startsWith("/>")?" ":"";a+=r===N?i+E:d>=0?(s.push(n),i.slice(0,d)+C+i.slice(d)+T+h):i+T+(-2===d?t:h)}return[Y(e,a+(e[i]||"<?>")+(2===t?"</svg>":3===t?"</math>":"")),s]})(e,t);if(this.el=W.createElement(l,i),Z.currentNode=this.el.content,2===t||3===t){const e=this.el.content.firstChild;e.replaceWith(...e.childNodes)}for(;null!==(s=Z.nextNode())&&n.length<r;){if(1===s.nodeType){if(s.hasAttributes())for(const e of s.getAttributeNames())if(e.endsWith(C)){const t=d[a++],i=s.getAttribute(e).split(T),r=/([.?@])?(.*)/.exec(t);n.push({type:1,index:o,name:r[2],strings:i,ctor:"."===r[1]?ee:"?"===r[1]?te:"@"===r[1]?ie:Q}),s.removeAttribute(e)}else e.startsWith(T)&&(n.push({type:6,index:o}),s.removeAttribute(e));if(F.test(s.tagName)){const e=s.textContent.split(T),t=e.length-1;if(t>0){s.textContent=D?D.emptyScript:"";for(let i=0;i<t;i++)s.append(e[i],I()),Z.nextNode(),n.push({type:2,index:++o});s.append(e[t],I())}}}else if(8===s.nodeType)if(s.data===A)n.push({type:2,index:o});else{let e=-1;for(;-1!==(e=s.data.indexOf(T,e+1));)n.push({type:7,index:o}),e+=T.length-1}o++}}static createElement(e,t){const i=P.createElement("template");return i.innerHTML=e,i}}function K(e,t,i=e,s){if(t===j)return t;let o=void 0!==s?i._$Co?.[s]:i._$Cl;const a=R(t)?void 0:t._$litDirective$;return o?.constructor!==a&&(o?._$AO?.(!1),void 0===a?o=void 0:(o=new a(e),o._$AT(e,i,s)),void 0!==s?(i._$Co??=[])[s]=o:i._$Cl=o),void 0!==o&&(t=K(e,o._$AS(e,t.values),o,s)),t}class G{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:i}=this._$AD,s=(e?.creationScope??P).importNode(t,!0);Z.currentNode=s;let o=Z.nextNode(),a=0,r=0,n=i[0];for(;void 0!==n;){if(a===n.index){let t;2===n.type?t=new J(o,o.nextSibling,this,e):1===n.type?t=new n.ctor(o,n.name,n.strings,this,e):6===n.type&&(t=new se(o,this,e)),this._$AV.push(t),n=i[++r]}a!==n?.index&&(o=Z.nextNode(),a++)}return Z.currentNode=P,s}p(e){let t=0;for(const i of this._$AV)void 0!==i&&(void 0!==i.strings?(i._$AI(e,i,t),t+=i.strings.length-2):i._$AI(e[t])),t++}}class J{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(e,t,i,s){this.type=2,this._$AH=q,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=i,this.options=s,this._$Cv=s?.isConnected??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return void 0!==t&&11===e?.nodeType&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=K(this,e,t),R(e)?e===q||null==e||""===e?(this._$AH!==q&&this._$AR(),this._$AH=q):e!==this._$AH&&e!==j&&this._(e):void 0!==e._$litType$?this.$(e):void 0!==e.nodeType?this.T(e):(e=>M(e)||"function"==typeof e?.[Symbol.iterator])(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==q&&R(this._$AH)?this._$AA.nextSibling.data=e:this.T(P.createTextNode(e)),this._$AH=e}$(e){const{values:t,_$litType$:i}=e,s="number"==typeof i?this._$AC(e):(void 0===i.el&&(i.el=W.createElement(Y(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===s)this._$AH.p(t);else{const e=new G(s,this),i=e.u(this.options);e.p(t),this.T(i),this._$AH=e}}_$AC(e){let t=X.get(e.strings);return void 0===t&&X.set(e.strings,t=new W(e)),t}k(e){M(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let i,s=0;for(const o of e)s===t.length?t.push(i=new J(this.O(I()),this.O(I()),this,this.options)):i=t[s],i._$AI(o),s++;s<t.length&&(this._$AR(i&&i._$AB.nextSibling,s),t.length=s)}_$AR(e=this._$AA.nextSibling,t){for(this._$AP?.(!1,!0,t);e!==this._$AB;){const t=k(e).nextSibling;k(e).remove(),e=t}}setConnected(e){void 0===this._$AM&&(this._$Cv=e,this._$AP?.(e))}}class Q{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,i,s,o){this.type=1,this._$AH=q,this._$AN=void 0,this.element=e,this.name=t,this._$AM=s,this.options=o,i.length>2||""!==i[0]||""!==i[1]?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=q}_$AI(e,t=this,i,s){const o=this.strings;let a=!1;if(void 0===o)e=K(this,e,t,0),a=!R(e)||e!==this._$AH&&e!==j,a&&(this._$AH=e);else{const s=e;let r,n;for(e=o[0],r=0;r<o.length-1;r++)n=K(this,s[i+r],t,r),n===j&&(n=this._$AH[r]),a||=!R(n)||n!==this._$AH[r],n===q?e=q:e!==q&&(e+=(n??"")+o[r+1]),this._$AH[r]=n}a&&!s&&this.j(e)}j(e){e===q?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class ee extends Q{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===q?void 0:e}}class te extends Q{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==q)}}class ie extends Q{constructor(e,t,i,s,o){super(e,t,i,s,o),this.type=5}_$AI(e,t=this){if((e=K(this,e,t,0)??q)===j)return;const i=this._$AH,s=e===q&&i!==q||e.capture!==i.capture||e.once!==i.once||e.passive!==i.passive,o=e!==q&&(i===q||s);s&&this.element.removeEventListener(this.name,this,i),o&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,e):this._$AH.handleEvent(e)}}class se{constructor(e,t,i){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(e){K(this,e)}}const oe={I:J},ae=w.litHtmlPolyfillSupport;ae?.(W,J),(w.litHtmlVersions??=[]).push("3.3.3");const re=globalThis;let ne=class extends ${constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const e=super.createRenderRoot();return this.renderOptions.renderBefore??=e.firstChild,e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=((e,t,i)=>{const s=i?.renderBefore??t;let o=s._$litPart$;if(void 0===o){const e=i?.renderBefore??null;s._$litPart$=o=new J(t.insertBefore(I(),e),e,void 0,i??{})}return o._$AI(e),o})(t,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return j}};ne._$litElement$=!0,ne.finalized=!0,re.litElementHydrateSupport?.({LitElement:ne});const le=re.litElementPolyfillSupport;le?.({LitElement:ne}),(re.litElementVersions??=[]).push("4.2.2");const de={attribute:!0,type:String,converter:f,reflect:!1,hasChanged:y},ce=(e=de,t,i)=>{const{kind:s,metadata:o}=i;let a=globalThis.litPropertyMetadata.get(o);if(void 0===a&&globalThis.litPropertyMetadata.set(o,a=new Map),"setter"===s&&((e=Object.create(e)).wrapped=!0),a.set(i.name,e),"accessor"===s){const{name:s}=i;return{set(i){const o=t.get.call(this);t.set.call(this,i),this.requestUpdate(s,o,e,!0,i)},init(t){return void 0!==t&&this.C(s,void 0,e,t),t}}}if("setter"===s){const{name:s}=i;return function(i){const o=this[s];t.call(this,i),this.requestUpdate(s,o,e,!0,i)}}throw Error("Unsupported decorator location: "+s)};function he(e){return(t,i)=>"object"==typeof i?ce(e,t,i):((e,t,i)=>{const s=t.hasOwnProperty(i);return t.constructor.createProperty(i,e),s?Object.getOwnPropertyDescriptor(t,i):void 0})(e,t,i)}function pe(e){return he({...e,state:!0,attribute:!1})}const ge=e=>e,ue=e=>customElements.get(e)?ge:(e=>(t,i)=>{void 0!==i?i.addInitializer(()=>{customElements.define(e,t)}):customElements.define(e,t)})(e);class me{constructor(e){this.hass=e}listDevices(){return this.hass.connection.sendMessagePromise({type:"hair/devices"})}getDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/device",device_id:e})}createDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/device/create",...e})}updateDevice(e,t){return this.hass.connection.sendMessagePromise({type:"hair/device/update",device_id:e,...t})}deleteDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/device/delete",device_id:e})}duplicateDevice(e,t){return this.hass.connection.sendMessagePromise({type:"hair/device/duplicate",device_id:e,new_name:t})}deleteCommand(e,t){return this.hass.connection.sendMessagePromise({type:"hair/command/delete",device_id:e,command_id:t})}setCommandTxForceRaw(e,t,i){return this.hass.connection.sendMessagePromise({type:"hair/command/set-tx-force-raw",device_id:e,command_id:t,tx_force_raw:i})}reorderCommands(e,t){return this.hass.connection.sendMessagePromise({type:"hair/device/reorder-commands",device_id:e,command_ids:t})}reorderDevices(e){return this.hass.connection.sendMessagePromise({type:"hair/devices/reorder",device_ids:e})}sendCommand(e,t){return this.hass.connection.sendMessagePromise({type:"hair/command/send",device_id:e,command_id:t})}listTemplates(e){return this.hass.connection.sendMessagePromise({type:"hair/templates",device_type:e})}listCaptureProviders(){return this.hass.connection.sendMessagePromise({type:"hair/capture/providers"})}listReceivers(){return this.hass.connection.sendMessagePromise({type:"hair/receivers"})}getSnifferStatus(){return this.hass.connection.sendMessagePromise({type:"hair/sniffer/status"})}getCodeBrands(){return this.hass.connection.sendMessagePromise({type:"hair/codes/brands"})}importCodeRemote(e,t){const i={type:"hair/codes/import-remote",codebook_id:e};return t&&(i.name=t),this.hass.connection.sendMessagePromise(i)}async startCapture(e,t,i){let s=null;const o=await this.hass.connection.subscribeMessage(e=>{e.type?.startsWith("capture_")?i(e):e.session_id&&(s=e)},{type:"hair/capture/start",device_id:e,timeout:t});if(await Promise.resolve(),null===s)throw new Error("Capture session did not start");return{session:s,unsubscribe:o}}cancelCapture(e){return this.hass.connection.sendMessagePromise({type:"hair/capture/cancel",session_id:e})}saveCapturedCommand(e){return this.hass.connection.sendMessagePromise({type:"hair/capture/save",...e})}getActionOptions(e){return this.hass.connection.sendMessagePromise({type:"hair/device/action-options",device_type:e})}updateMapping(e,t,i){return this.hass.connection.sendMessagePromise({type:"hair/device/update-mapping",device_id:e,command_name:t,action_key:i})}getUnknownDevices(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/devices",...e})}getUnknownDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/device",device_id:e})}dismissUnknown(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/dismiss",device_id:e})}undismissUnknown(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/undismiss",device_id:e})}assignSignal(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/assign",...e})}assignToNewDevice(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/assign-new-device",...e})}deleteSignal(e,t){return this.hass.connection.sendMessagePromise({type:"hair/unknown/signal/delete",device_id:e,signal_id:t})}testSignal(e,t){const i={type:"hair/unknown/test",signal_id:e};return t&&(i.emitter_entity_id=t),this.hass.connection.sendMessagePromise(i)}renameUnknown(e,t){return this.hass.connection.sendMessagePromise({type:"hair/unknown/rename",device_id:e,label:t})}clearUnknowns(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/clear",...e?{source:e}:{}})}setSignalAlias(e,t,i){return this.hass.connection.sendMessagePromise({type:"hair/unknown/signal/set-alias",device_id:e,signal_id:t,alias:i})}reorderUnknownDevices(e,t){return this.hass.connection.sendMessagePromise({type:"hair/unknown/reorder",source:e,device_ids:t})}reorderUnknownSignals(e,t){return this.hass.connection.sendMessagePromise({type:"hair/unknown/signal/reorder",device_id:e,signal_ids:t})}createRemote(e){return this.hass.connection.sendMessagePromise({type:"hair/clip/create-remote",name:e})}createSignal(e){return this.hass.connection.sendMessagePromise({type:"hair/clip/create-signal",...e})}editSignalPronto(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/signal/edit-pronto",...e})}validatePronto(e){return this.hass.connection.sendMessagePromise({type:"hair/clip/validate-pronto",pronto:e})}snapPreview(e){return this.hass.connection.sendMessagePromise({type:"hair/unknown/signal/snap-preview",...e})}updateCommand(e){return this.hass.connection.sendMessagePromise({type:"hair/command/update",...e})}deleteRemote(e){return this.hass.connection.sendMessagePromise({type:"hair/clip/delete-remote",device_id:e})}listPluckVendors(){return this.hass.connection.sendMessagePromise({type:"hair/pluck/list-vendors"})}runPluck(e){return this.hass.connection.sendMessagePromise({type:"hair/pluck/run",...e})}createPluckedBlaster(e){return this.hass.connection.sendMessagePromise({type:"hair/pluck/create-blaster",...e})}createPluckedSignal(e){return this.hass.connection.sendMessagePromise({type:"hair/pluck/create-signal",...e})}deletePluckedBlaster(e){return this.hass.connection.sendMessagePromise({type:"hair/pluck/delete-blaster",device_id:e})}async subscribeUnknownSignals(e){return this.hass.connection.subscribeEvents(t=>e(t.data),"hair_signal_detected")}async subscribeSignalRemoved(e){return this.hass.connection.subscribeEvents(t=>e(t.data),"hair_signal_removed")}async subscribeSignalUpdated(e){return this.hass.connection.subscribeEvents(t=>e(t.data),"hair_signal_updated")}async subscribeDismissActivity(e){return this.hass.connection.subscribeEvents(t=>e(t.data),"hair_dismiss_activity")}listTriggers(){return this.hass.connection.sendMessagePromise({type:"hair/triggers"})}createTrigger(e){return this.hass.connection.sendMessagePromise({type:"hair/trigger/create",...e})}updateTrigger(e,t){return this.hass.connection.sendMessagePromise({type:"hair/trigger/update",trigger_id:e,...t})}deleteTrigger(e){return this.hass.connection.sendMessagePromise({type:"hair/trigger/delete",trigger_id:e})}async subscribeTriggerFired(e){return this.hass.connection.subscribeMessage(e,{type:"hair/trigger/subscribe"})}}const ve=e=>(...t)=>({_$litDirective$:e,values:t});let _e=class{constructor(e){}get _$AU(){return this._$AM._$AU}_$AT(e,t,i){this._$Ct=e,this._$AM=t,this._$Ci=i}_$AS(e,t){return this.update(e,t)}update(e,t){return this.render(...t)}};const{I:be}=oe,fe=e=>e,ye=()=>document.createComment(""),xe=(e,t,i)=>{const s=e._$AA.parentNode,o=void 0===t?e._$AB:t._$AA;if(void 0===i){const t=s.insertBefore(ye(),o),a=s.insertBefore(ye(),o);i=new be(t,a,e,e.options)}else{const t=i._$AB.nextSibling,a=i._$AM,r=a!==e;if(r){let t;i._$AQ?.(e),i._$AM=e,void 0!==i._$AP&&(t=e._$AU)!==a._$AU&&i._$AP(t)}if(t!==o||r){let e=i._$AA;for(;e!==t;){const t=fe(e).nextSibling;fe(s).insertBefore(e,o),e=t}}}return i},$e=(e,t,i=e)=>(e._$AI(t,i),e),we={},ke=(e,t=we)=>e._$AH=t,De=e=>{e._$AR(),e._$AA.remove()},Se=ve(class extends _e{constructor(){super(...arguments),this.key=q}render(e,t){return this.key=e,t}update(e,[t,i]){return t!==this.key&&(ke(e),this.key=t),i}}),Ce=(e,t,i)=>{const s=new Map;for(let o=t;o<=i;o++)s.set(e[o],o);return s},Te=ve(class extends _e{constructor(e){if(super(e),2!==e.type)throw Error("repeat() can only be used in text expressions")}dt(e,t,i){let s;void 0===i?i=t:void 0!==t&&(s=t);const o=[],a=[];let r=0;for(const t of e)o[r]=s?s(t,r):r,a[r]=i(t,r),r++;return{values:a,keys:o}}render(e,t,i){return this.dt(e,t,i).values}update(e,[t,i,s]){const o=(e=>e._$AH)(e),{values:a,keys:r}=this.dt(t,i,s);if(!Array.isArray(o))return this.ut=r,a;const n=this.ut??=[],l=[];let d,c,h=0,p=o.length-1,g=0,u=a.length-1;for(;h<=p&&g<=u;)if(null===o[h])h++;else if(null===o[p])p--;else if(n[h]===r[g])l[g]=$e(o[h],a[g]),h++,g++;else if(n[p]===r[u])l[u]=$e(o[p],a[u]),p--,u--;else if(n[h]===r[u])l[u]=$e(o[h],a[u]),xe(e,l[u+1],o[h]),h++,u--;else if(n[p]===r[g])l[g]=$e(o[p],a[g]),xe(e,o[h],o[p]),p--,g++;else if(void 0===d&&(d=Ce(r,g,u),c=Ce(n,h,p)),d.has(n[h]))if(d.has(n[p])){const t=c.get(r[g]),i=void 0!==t?o[t]:null;if(null===i){const t=xe(e,o[h]);$e(t,a[g]),l[g]=t}else l[g]=$e(i,a[g]),xe(e,o[h],i),o[t]=null;g++}else De(o[p]),p--;else De(o[h]),h++;for(;g<=u;){const t=xe(e,l[u+1]);$e(t,a[g]),l[g++]=t}for(;h<=p;){const e=o[h++];null!==e&&De(e)}return this.ut=r,ke(e,l),j}});function Ae(e,t,i){return(t=function(e){var t=function(e,t){if("object"!=typeof e||!e)return e;var i=e[Symbol.toPrimitive];if(void 0!==i){var s=i.call(e,t);if("object"!=typeof s)return s;throw new TypeError("@@toPrimitive must return a primitive value.")}return String(e)}(e,"string");return"symbol"==typeof t?t:t+""}(t))in e?Object.defineProperty(e,t,{value:i,enumerable:!0,configurable:!0,writable:!0}):e[t]=i,e}function Ee(){return Ee=Object.assign?Object.assign.bind():function(e){for(var t=1;t<arguments.length;t++){var i=arguments[t];for(var s in i)({}).hasOwnProperty.call(i,s)&&(e[s]=i[s])}return e},Ee.apply(null,arguments)}function Pe(e,t){var i=Object.keys(e);if(Object.getOwnPropertySymbols){var s=Object.getOwnPropertySymbols(e);t&&(s=s.filter(function(t){return Object.getOwnPropertyDescriptor(e,t).enumerable})),i.push.apply(i,s)}return i}function Ie(e){for(var t=1;t<arguments.length;t++){var i=null!=arguments[t]?arguments[t]:{};t%2?Pe(Object(i),!0).forEach(function(t){Ae(e,t,i[t])}):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(i)):Pe(Object(i)).forEach(function(t){Object.defineProperty(e,t,Object.getOwnPropertyDescriptor(i,t))})}return e}function Re(e){return Re="function"==typeof Symbol&&"symbol"==typeof Symbol.iterator?function(e){return typeof e}:function(e){return e&&"function"==typeof Symbol&&e.constructor===Symbol&&e!==Symbol.prototype?"symbol":typeof e},Re(e)}function Me(e){if("undefined"!=typeof window&&window.navigator)return!!navigator.userAgent.match(e)}var He=Me(/(?:Trident.*rv[ :]?11\.|msie|iemobile|Windows Phone)/i),Ne=Me(/Edge/i),ze=Me(/firefox/i),Le=Me(/safari/i)&&!Me(/chrome/i)&&!Me(/android/i),Ve=Me(/iP(ad|od|hone)/i),Oe=Me(/chrome/i)&&Me(/android/i),Ue={capture:!1,passive:!1};function Fe(e,t,i){e.addEventListener(t,i,!He&&Ue)}function Be(e,t,i){e.removeEventListener(t,i,!He&&Ue)}function je(e,t){if(t){if(">"===t[0]&&(t=t.substring(1)),e)try{if(e.matches)return e.matches(t);if(e.msMatchesSelector)return e.msMatchesSelector(t);if(e.webkitMatchesSelector)return e.webkitMatchesSelector(t)}catch(e){return!1}return!1}}function qe(e){return e.host&&e!==document&&e.host.nodeType&&e.host!==e?e.host:e.parentNode}function Xe(e,t,i,s){if(e){i=i||document;do{if(null!=t&&(">"===t[0]?e.parentNode===i&&je(e,t):je(e,t))||s&&e===i)return e;if(e===i)break}while(e=qe(e))}return null}var Ze,Ye=/\s+/g;function We(e,t,i){if(e&&t)if(e.classList)e.classList[i?"add":"remove"](t);else{var s=(" "+e.className+" ").replace(Ye," ").replace(" "+t+" "," ");e.className=(s+(i?" "+t:"")).replace(Ye," ")}}function Ke(e,t,i){var s=e&&e.style;if(s){if(void 0===i)return document.defaultView&&document.defaultView.getComputedStyle?i=document.defaultView.getComputedStyle(e,""):e.currentStyle&&(i=e.currentStyle),void 0===t?i:i[t];t in s||-1!==t.indexOf("webkit")||(t="-webkit-"+t),s[t]=i+("string"==typeof i?"":"px")}}function Ge(e,t){var i="";if("string"==typeof e)i=e;else do{var s=Ke(e,"transform");s&&"none"!==s&&(i=s+" "+i)}while(!t&&(e=e.parentNode));var o=window.DOMMatrix||window.WebKitCSSMatrix||window.CSSMatrix||window.MSCSSMatrix;return o&&new o(i)}function Je(e,t,i){if(e){var s=e.getElementsByTagName(t),o=0,a=s.length;if(i)for(;o<a;o++)i(s[o],o);return s}return[]}function Qe(){return document.scrollingElement||document.documentElement}function et(e,t,i,s,o){if(e.getBoundingClientRect||e===window){var a,r,n,l,d,c,h;if(e!==window&&e.parentNode&&e!==Qe()?(r=(a=e.getBoundingClientRect()).top,n=a.left,l=a.bottom,d=a.right,c=a.height,h=a.width):(r=0,n=0,l=window.innerHeight,d=window.innerWidth,c=window.innerHeight,h=window.innerWidth),(t||i)&&e!==window&&(o=o||e.parentNode,!He))do{if(o&&o.getBoundingClientRect&&("none"!==Ke(o,"transform")||i&&"static"!==Ke(o,"position"))){var p=o.getBoundingClientRect();r-=p.top+parseInt(Ke(o,"border-top-width")),n-=p.left+parseInt(Ke(o,"border-left-width")),l=r+a.height,d=n+a.width;break}}while(o=o.parentNode);if(s&&e!==window){var g=Ge(o||e),u=g&&g.a,m=g&&g.d;g&&(l=(r/=m)+(c/=m),d=(n/=u)+(h/=u))}return{top:r,left:n,bottom:l,right:d,width:h,height:c}}}function tt(e,t,i){for(var s=rt(e,!0),o=et(e)[t];s;){if(!(o>=et(s)[i]))return s;if(s===Qe())break;s=rt(s,!1)}return!1}function it(e,t,i,s){for(var o=0,a=0,r=e.children;a<r.length;){if("none"!==r[a].style.display&&r[a]!==di.ghost&&(s||r[a]!==di.dragged)&&Xe(r[a],i.draggable,e,!1)){if(o===t)return r[a];o++}a++}return null}function st(e,t){for(var i=e.lastElementChild;i&&(i===di.ghost||"none"===Ke(i,"display")||t&&!je(i,t));)i=i.previousElementSibling;return i||null}function ot(e,t){var i=0;if(!e||!e.parentNode)return-1;for(;e=e.previousElementSibling;)"TEMPLATE"===e.nodeName.toUpperCase()||e===di.clone||t&&!je(e,t)||i++;return i}function at(e){var t=0,i=0,s=Qe();if(e)do{var o=Ge(e),a=o.a,r=o.d;t+=e.scrollLeft*a,i+=e.scrollTop*r}while(e!==s&&(e=e.parentNode));return[t,i]}function rt(e,t){if(!e||!e.getBoundingClientRect)return Qe();var i=e,s=!1;do{if(i.clientWidth<i.scrollWidth||i.clientHeight<i.scrollHeight){var o=Ke(i);if(i.clientWidth<i.scrollWidth&&("auto"==o.overflowX||"scroll"==o.overflowX)||i.clientHeight<i.scrollHeight&&("auto"==o.overflowY||"scroll"==o.overflowY)){if(!i.getBoundingClientRect||i===document.body)return Qe();if(s||t)return i;s=!0}}}while(i=i.parentNode);return Qe()}function nt(e,t){return Math.round(e.top)===Math.round(t.top)&&Math.round(e.left)===Math.round(t.left)&&Math.round(e.height)===Math.round(t.height)&&Math.round(e.width)===Math.round(t.width)}function lt(e,t){return function(){if(!Ze){var i=arguments;1===i.length?e.call(this,i[0]):e.apply(this,i),Ze=setTimeout(function(){Ze=void 0},t)}}}function dt(e,t,i){e.scrollLeft+=t,e.scrollTop+=i}function ct(e){var t=window.Polymer,i=window.jQuery||window.Zepto;return t&&t.dom?t.dom(e).cloneNode(!0):i?i(e).clone(!0)[0]:e.cloneNode(!0)}function ht(e,t,i){var s={};return Array.from(e.children).forEach(function(o){var a,r,n,l;if(Xe(o,t.draggable,e,!1)&&!o.animated&&o!==i){var d=et(o);s.left=Math.min(null!==(a=s.left)&&void 0!==a?a:1/0,d.left),s.top=Math.min(null!==(r=s.top)&&void 0!==r?r:1/0,d.top),s.right=Math.max(null!==(n=s.right)&&void 0!==n?n:-1/0,d.right),s.bottom=Math.max(null!==(l=s.bottom)&&void 0!==l?l:-1/0,d.bottom)}}),s.width=s.right-s.left,s.height=s.bottom-s.top,s.x=s.left,s.y=s.top,s}var pt="Sortable"+(new Date).getTime();var gt=[],ut={initializeByDefault:!0},mt={mount:function(e){for(var t in ut)ut.hasOwnProperty(t)&&!(t in e)&&(e[t]=ut[t]);gt.forEach(function(t){if(t.pluginName===e.pluginName)throw"Sortable: Cannot mount plugin ".concat(e.pluginName," more than once")}),gt.push(e)},pluginEvent:function(e,t,i){var s=this;this.eventCanceled=!1,i.cancel=function(){s.eventCanceled=!0};var o=e+"Global";gt.forEach(function(s){t[s.pluginName]&&(t[s.pluginName][o]&&t[s.pluginName][o](Ie({sortable:t},i)),t.options[s.pluginName]&&t[s.pluginName][e]&&t[s.pluginName][e](Ie({sortable:t},i)))})},initializePlugins:function(e,t,i,s){for(var o in gt.forEach(function(s){var o=s.pluginName;if(e.options[o]||s.initializeByDefault){var a=new s(e,t,e.options);a.sortable=e,a.options=e.options,e[o]=a,Ee(i,a.defaults)}}),e.options)if(e.options.hasOwnProperty(o)){var a=this.modifyOption(e,o,e.options[o]);void 0!==a&&(e.options[o]=a)}},getEventProperties:function(e,t){var i={};return gt.forEach(function(s){"function"==typeof s.eventProperties&&Ee(i,s.eventProperties.call(t[s.pluginName],e))}),i},modifyOption:function(e,t,i){var s;return gt.forEach(function(o){e[o.pluginName]&&o.optionListeners&&"function"==typeof o.optionListeners[t]&&(s=o.optionListeners[t].call(e[o.pluginName],i))}),s}},vt=["evt"],_t=function(e,t){var i=arguments.length>2&&void 0!==arguments[2]?arguments[2]:{},s=i.evt,o=function(e,t){if(null==e)return{};var i,s,o=function(e,t){if(null==e)return{};var i={};for(var s in e)if({}.hasOwnProperty.call(e,s)){if(-1!==t.indexOf(s))continue;i[s]=e[s]}return i}(e,t);if(Object.getOwnPropertySymbols){var a=Object.getOwnPropertySymbols(e);for(s=0;s<a.length;s++)i=a[s],-1===t.indexOf(i)&&{}.propertyIsEnumerable.call(e,i)&&(o[i]=e[i])}return o}(i,vt);mt.pluginEvent.bind(di)(e,t,Ie({dragEl:ft,parentEl:yt,ghostEl:xt,rootEl:$t,nextEl:wt,lastDownEl:kt,cloneEl:Dt,cloneHidden:St,dragStarted:Vt,putSortable:It,activeSortable:di.active,originalEvent:s,oldIndex:Ct,oldDraggableIndex:At,newIndex:Tt,newDraggableIndex:Et,hideGhostForTarget:ai,unhideGhostForTarget:ri,cloneNowHidden:function(){St=!0},cloneNowShown:function(){St=!1},dispatchSortableEvent:function(e){bt({sortable:t,name:e,originalEvent:s})}},o))};function bt(e){!function(e){var t=e.sortable,i=e.rootEl,s=e.name,o=e.targetEl,a=e.cloneEl,r=e.toEl,n=e.fromEl,l=e.oldIndex,d=e.newIndex,c=e.oldDraggableIndex,h=e.newDraggableIndex,p=e.originalEvent,g=e.putSortable,u=e.extraEventProperties;if(t=t||i&&i[pt]){var m,v=t.options,_="on"+s.charAt(0).toUpperCase()+s.substr(1);!window.CustomEvent||He||Ne?(m=document.createEvent("Event")).initEvent(s,!0,!0):m=new CustomEvent(s,{bubbles:!0,cancelable:!0}),m.to=r||i,m.from=n||i,m.item=o||i,m.clone=a,m.oldIndex=l,m.newIndex=d,m.oldDraggableIndex=c,m.newDraggableIndex=h,m.originalEvent=p,m.pullMode=g?g.lastPutMode:void 0;var b=Ie(Ie({},u),mt.getEventProperties(s,t));for(var f in b)m[f]=b[f];i&&i.dispatchEvent(m),v[_]&&v[_].call(t,m)}}(Ie({putSortable:It,cloneEl:Dt,targetEl:ft,rootEl:$t,oldIndex:Ct,oldDraggableIndex:At,newIndex:Tt,newDraggableIndex:Et},e))}var ft,yt,xt,$t,wt,kt,Dt,St,Ct,Tt,At,Et,Pt,It,Rt,Mt,Ht,Nt,zt,Lt,Vt,Ot,Ut,Ft,Bt,jt=!1,qt=!1,Xt=[],Zt=!1,Yt=!1,Wt=[],Kt=!1,Gt=[],Jt="undefined"!=typeof document,Qt=Ve,ei=Ne||He?"cssFloat":"float",ti=Jt&&!Oe&&!Ve&&"draggable"in document.createElement("div"),ii=function(){if(Jt){if(He)return!1;var e=document.createElement("x");return e.style.cssText="pointer-events:auto","auto"===e.style.pointerEvents}}(),si=function(e,t){var i=Ke(e),s=parseInt(i.width)-parseInt(i.paddingLeft)-parseInt(i.paddingRight)-parseInt(i.borderLeftWidth)-parseInt(i.borderRightWidth),o=it(e,0,t),a=it(e,1,t),r=o&&Ke(o),n=a&&Ke(a),l=r&&parseInt(r.marginLeft)+parseInt(r.marginRight)+et(o).width,d=n&&parseInt(n.marginLeft)+parseInt(n.marginRight)+et(a).width;if("flex"===i.display)return"column"===i.flexDirection||"column-reverse"===i.flexDirection?"vertical":"horizontal";if("grid"===i.display)return i.gridTemplateColumns.split(" ").length<=1?"vertical":"horizontal";if(o&&r.float&&"none"!==r.float){var c="left"===r.float?"left":"right";return!a||"both"!==n.clear&&n.clear!==c?"horizontal":"vertical"}return o&&("block"===r.display||"flex"===r.display||"table"===r.display||"grid"===r.display||l>=s&&"none"===i[ei]||a&&"none"===i[ei]&&l+d>s)?"vertical":"horizontal"},oi=function(e){function t(e,i){return function(s,o,a,r){var n=s.options.group.name&&o.options.group.name&&s.options.group.name===o.options.group.name;if(null==e&&(i||n))return!0;if(null==e||!1===e)return!1;if(i&&"clone"===e)return e;if("function"==typeof e)return t(e(s,o,a,r),i)(s,o,a,r);var l=(i?s:o).options.group.name;return!0===e||"string"==typeof e&&e===l||e.join&&e.indexOf(l)>-1}}var i={},s=e.group;s&&"object"==Re(s)||(s={name:s}),i.name=s.name,i.checkPull=t(s.pull,!0),i.checkPut=t(s.put),i.revertClone=s.revertClone,e.group=i},ai=function(){!ii&&xt&&Ke(xt,"display","none")},ri=function(){!ii&&xt&&Ke(xt,"display","")};Jt&&!Oe&&document.addEventListener("click",function(e){if(qt)return e.preventDefault(),e.stopPropagation&&e.stopPropagation(),e.stopImmediatePropagation&&e.stopImmediatePropagation(),qt=!1,!1},!0);var ni=function(e){if(ft){var t=function(e,t){var i;return Xt.some(function(s){var o=s[pt].options.emptyInsertThreshold;if(o&&!st(s)){var a=et(s),r=e>=a.left-o&&e<=a.right+o,n=t>=a.top-o&&t<=a.bottom+o;return r&&n?i=s:void 0}}),i}((e=e.touches?e.touches[0]:e).clientX,e.clientY);if(t){var i={};for(var s in e)e.hasOwnProperty(s)&&(i[s]=e[s]);i.target=i.rootEl=t,i.preventDefault=void 0,i.stopPropagation=void 0,t[pt]._onDragOver(i)}}},li=function(e){ft&&ft.parentNode[pt]._isOutsideThisEl(e.target)};function di(e,t){if(!e||!e.nodeType||1!==e.nodeType)throw"Sortable: `el` must be an HTMLElement, not ".concat({}.toString.call(e));this.el=e,this.options=t=Ee({},t),e[pt]=this;var i,s,o={group:null,sort:!0,disabled:!1,store:null,handle:null,draggable:/^[uo]l$/i.test(e.nodeName)?">li":">*",swapThreshold:1,invertSwap:!1,invertedSwapThreshold:null,removeCloneOnHide:!0,direction:function(){return si(e,this.options)},ghostClass:"sortable-ghost",chosenClass:"sortable-chosen",dragClass:"sortable-drag",ignore:"a, img",filter:null,preventOnFilter:!0,animation:0,easing:null,setData:function(e,t){e.setData("Text",t.textContent)},dropBubble:!1,dragoverBubble:!1,dataIdAttr:"data-id",delay:0,delayOnTouchOnly:!1,touchStartThreshold:(Number.parseInt?Number:window).parseInt(window.devicePixelRatio,10)||1,forceFallback:!1,fallbackClass:"sortable-fallback",fallbackOnBody:!1,fallbackTolerance:0,fallbackOffset:{x:0,y:0},supportPointer:!1!==di.supportPointer&&"PointerEvent"in window&&(!Le||Ve),emptyInsertThreshold:5};for(var a in mt.initializePlugins(this,e,o),o)!(a in t)&&(t[a]=o[a]);for(var r in oi(t),this)"_"===r.charAt(0)&&"function"==typeof this[r]&&(this[r]=this[r].bind(this));this.nativeDraggable=!t.forceFallback&&ti,this.nativeDraggable&&(this.options.touchStartThreshold=1),t.supportPointer?Fe(e,"pointerdown",this._onTapStart):(Fe(e,"mousedown",this._onTapStart),Fe(e,"touchstart",this._onTapStart)),this.nativeDraggable&&(Fe(e,"dragover",this),Fe(e,"dragenter",this)),Xt.push(this.el),t.store&&t.store.get&&this.sort(t.store.get(this)||[]),Ee(this,(s=[],{captureAnimationState:function(){s=[],this.options.animation&&[].slice.call(this.el.children).forEach(function(e){if("none"!==Ke(e,"display")&&e!==di.ghost){s.push({target:e,rect:et(e)});var t=Ie({},s[s.length-1].rect);if(e.thisAnimationDuration){var i=Ge(e,!0);i&&(t.top-=i.f,t.left-=i.e)}e.fromRect=t}})},addAnimationState:function(e){s.push(e)},removeAnimationState:function(e){s.splice(function(e,t){for(var i in e)if(e.hasOwnProperty(i))for(var s in t)if(t.hasOwnProperty(s)&&t[s]===e[i][s])return Number(i);return-1}(s,{target:e}),1)},animateAll:function(e){var t=this;if(!this.options.animation)return clearTimeout(i),void("function"==typeof e&&e());var o=!1,a=0;s.forEach(function(e){var i=0,s=e.target,r=s.fromRect,n=et(s),l=s.prevFromRect,d=s.prevToRect,c=e.rect,h=Ge(s,!0);h&&(n.top-=h.f,n.left-=h.e),s.toRect=n,s.thisAnimationDuration&&nt(l,n)&&!nt(r,n)&&(c.top-n.top)/(c.left-n.left)===(r.top-n.top)/(r.left-n.left)&&(i=function(e,t,i,s){return Math.sqrt(Math.pow(t.top-e.top,2)+Math.pow(t.left-e.left,2))/Math.sqrt(Math.pow(t.top-i.top,2)+Math.pow(t.left-i.left,2))*s.animation}(c,l,d,t.options)),nt(n,r)||(s.prevFromRect=r,s.prevToRect=n,i||(i=t.options.animation),t.animate(s,c,n,i)),i&&(o=!0,a=Math.max(a,i),clearTimeout(s.animationResetTimer),s.animationResetTimer=setTimeout(function(){s.animationTime=0,s.prevFromRect=null,s.fromRect=null,s.prevToRect=null,s.thisAnimationDuration=null},i),s.thisAnimationDuration=i)}),clearTimeout(i),o?i=setTimeout(function(){"function"==typeof e&&e()},a):"function"==typeof e&&e(),s=[]},animate:function(e,t,i,s){if(s){Ke(e,"transition",""),Ke(e,"transform","");var o=Ge(this.el),a=o&&o.a,r=o&&o.d,n=(t.left-i.left)/(a||1),l=(t.top-i.top)/(r||1);e.animatingX=!!n,e.animatingY=!!l,Ke(e,"transform","translate3d("+n+"px,"+l+"px,0)"),this.forRepaintDummy=function(e){return e.offsetWidth}(e),Ke(e,"transition","transform "+s+"ms"+(this.options.easing?" "+this.options.easing:"")),Ke(e,"transform","translate3d(0,0,0)"),"number"==typeof e.animated&&clearTimeout(e.animated),e.animated=setTimeout(function(){Ke(e,"transition",""),Ke(e,"transform",""),e.animated=!1,e.animatingX=!1,e.animatingY=!1},s)}}}))}function ci(e,t,i,s,o,a,r,n){var l,d,c=e[pt],h=c.options.onMove;return!window.CustomEvent||He||Ne?(l=document.createEvent("Event")).initEvent("move",!0,!0):l=new CustomEvent("move",{bubbles:!0,cancelable:!0}),l.to=t,l.from=e,l.dragged=i,l.draggedRect=s,l.related=o||t,l.relatedRect=a||et(t),l.willInsertAfter=n,l.originalEvent=r,e.dispatchEvent(l),h&&(d=h.call(c,l,r)),d}function hi(e){e.draggable=!1}function pi(){Kt=!1}function gi(e){for(var t=e.tagName+e.className+e.src+e.href+e.textContent,i=t.length,s=0;i--;)s+=t.charCodeAt(i);return s.toString(36)}function ui(e){return setTimeout(e,0)}function mi(e){return clearTimeout(e)}di.prototype={constructor:di,_isOutsideThisEl:function(e){this.el.contains(e)||e===this.el||(Ot=null)},_getDirection:function(e,t){return"function"==typeof this.options.direction?this.options.direction.call(this,e,t,ft):this.options.direction},_onTapStart:function(e){if(e.cancelable){var t=this,i=this.el,s=this.options,o=s.preventOnFilter,a=e.type,r=e.touches&&e.touches[0]||e.pointerType&&"touch"===e.pointerType&&e,n=(r||e).target,l=e.target.shadowRoot&&(e.path&&e.path[0]||e.composedPath&&e.composedPath()[0])||n,d=s.filter;if(function(e){Gt.length=0;for(var t=e.getElementsByTagName("input"),i=t.length;i--;){var s=t[i];s.checked&&Gt.push(s)}}(i),!ft&&!(/mousedown|pointerdown/.test(a)&&0!==e.button||s.disabled)&&!l.isContentEditable&&(this.nativeDraggable||!Le||!n||"SELECT"!==n.tagName.toUpperCase())&&!((n=Xe(n,s.draggable,i,!1))&&n.animated||kt===n)){if(Ct=ot(n),At=ot(n,s.draggable),"function"==typeof d){if(d.call(this,e,n,this))return bt({sortable:t,rootEl:l,name:"filter",targetEl:n,toEl:i,fromEl:i}),_t("filter",t,{evt:e}),void(o&&e.preventDefault())}else if(d&&(d=d.split(",").some(function(s){if(s=Xe(l,s.trim(),i,!1))return bt({sortable:t,rootEl:s,name:"filter",targetEl:n,fromEl:i,toEl:i}),_t("filter",t,{evt:e}),!0})))return void(o&&e.preventDefault());s.handle&&!Xe(l,s.handle,i,!1)||this._prepareDragStart(e,r,n)}}},_prepareDragStart:function(e,t,i){var s,o=this,a=o.el,r=o.options,n=a.ownerDocument;if(i&&!ft&&i.parentNode===a){var l=et(i);if($t=a,yt=(ft=i).parentNode,wt=ft.nextSibling,kt=i,Pt=r.group,di.dragged=ft,Rt={target:ft,clientX:(t||e).clientX,clientY:(t||e).clientY},zt=Rt.clientX-l.left,Lt=Rt.clientY-l.top,this._lastX=(t||e).clientX,this._lastY=(t||e).clientY,ft.style["will-change"]="all",s=function(){_t("delayEnded",o,{evt:e}),di.eventCanceled?o._onDrop():(o._disableDelayedDragEvents(),!ze&&o.nativeDraggable&&(ft.draggable=!0),o._triggerDragStart(e,t),bt({sortable:o,name:"choose",originalEvent:e}),We(ft,r.chosenClass,!0))},r.ignore.split(",").forEach(function(e){Je(ft,e.trim(),hi)}),Fe(n,"dragover",ni),Fe(n,"mousemove",ni),Fe(n,"touchmove",ni),r.supportPointer?(Fe(n,"pointerup",o._onDrop),!this.nativeDraggable&&Fe(n,"pointercancel",o._onDrop)):(Fe(n,"mouseup",o._onDrop),Fe(n,"touchend",o._onDrop),Fe(n,"touchcancel",o._onDrop)),ze&&this.nativeDraggable&&(this.options.touchStartThreshold=4,ft.draggable=!0),_t("delayStart",this,{evt:e}),!r.delay||r.delayOnTouchOnly&&!t||this.nativeDraggable&&(Ne||He))s();else{if(di.eventCanceled)return void this._onDrop();r.supportPointer?(Fe(n,"pointerup",o._disableDelayedDrag),Fe(n,"pointercancel",o._disableDelayedDrag)):(Fe(n,"mouseup",o._disableDelayedDrag),Fe(n,"touchend",o._disableDelayedDrag),Fe(n,"touchcancel",o._disableDelayedDrag)),Fe(n,"mousemove",o._delayedDragTouchMoveHandler),Fe(n,"touchmove",o._delayedDragTouchMoveHandler),r.supportPointer&&Fe(n,"pointermove",o._delayedDragTouchMoveHandler),o._dragStartTimer=setTimeout(s,r.delay)}}},_delayedDragTouchMoveHandler:function(e){var t=e.touches?e.touches[0]:e;Math.max(Math.abs(t.clientX-this._lastX),Math.abs(t.clientY-this._lastY))>=Math.floor(this.options.touchStartThreshold/(this.nativeDraggable&&window.devicePixelRatio||1))&&this._disableDelayedDrag()},_disableDelayedDrag:function(){ft&&hi(ft),clearTimeout(this._dragStartTimer),this._disableDelayedDragEvents()},_disableDelayedDragEvents:function(){var e=this.el.ownerDocument;Be(e,"mouseup",this._disableDelayedDrag),Be(e,"touchend",this._disableDelayedDrag),Be(e,"touchcancel",this._disableDelayedDrag),Be(e,"pointerup",this._disableDelayedDrag),Be(e,"pointercancel",this._disableDelayedDrag),Be(e,"mousemove",this._delayedDragTouchMoveHandler),Be(e,"touchmove",this._delayedDragTouchMoveHandler),Be(e,"pointermove",this._delayedDragTouchMoveHandler)},_triggerDragStart:function(e,t){t=t||"touch"==e.pointerType&&e,!this.nativeDraggable||t?this.options.supportPointer?Fe(document,"pointermove",this._onTouchMove):Fe(document,t?"touchmove":"mousemove",this._onTouchMove):(Fe(ft,"dragend",this),Fe($t,"dragstart",this._onDragStart));try{document.selection?ui(function(){document.selection.empty()}):window.getSelection().removeAllRanges()}catch(e){}},_dragStarted:function(e,t){if(jt=!1,$t&&ft){_t("dragStarted",this,{evt:t}),this.nativeDraggable&&Fe(document,"dragover",li);var i=this.options;!e&&We(ft,i.dragClass,!1),We(ft,i.ghostClass,!0),di.active=this,e&&this._appendGhost(),bt({sortable:this,name:"start",originalEvent:t})}else this._nulling()},_emulateDragOver:function(){if(Mt){this._lastX=Mt.clientX,this._lastY=Mt.clientY,ai();for(var e=document.elementFromPoint(Mt.clientX,Mt.clientY),t=e;e&&e.shadowRoot&&(e=e.shadowRoot.elementFromPoint(Mt.clientX,Mt.clientY))!==t;)t=e;if(ft.parentNode[pt]._isOutsideThisEl(e),t)do{if(t[pt]&&t[pt]._onDragOver({clientX:Mt.clientX,clientY:Mt.clientY,target:e,rootEl:t})&&!this.options.dragoverBubble)break;e=t}while(t=qe(t));ri()}},_onTouchMove:function(e){if(Rt){var t=this.options,i=t.fallbackTolerance,s=t.fallbackOffset,o=e.touches?e.touches[0]:e,a=xt&&Ge(xt,!0),r=xt&&a&&a.a,n=xt&&a&&a.d,l=Qt&&Bt&&at(Bt),d=(o.clientX-Rt.clientX+s.x)/(r||1)+(l?l[0]-Wt[0]:0)/(r||1),c=(o.clientY-Rt.clientY+s.y)/(n||1)+(l?l[1]-Wt[1]:0)/(n||1);if(!di.active&&!jt){if(i&&Math.max(Math.abs(o.clientX-this._lastX),Math.abs(o.clientY-this._lastY))<i)return;this._onDragStart(e,!0)}if(xt){a?(a.e+=d-(Ht||0),a.f+=c-(Nt||0)):a={a:1,b:0,c:0,d:1,e:d,f:c};var h="matrix(".concat(a.a,",").concat(a.b,",").concat(a.c,",").concat(a.d,",").concat(a.e,",").concat(a.f,")");Ke(xt,"webkitTransform",h),Ke(xt,"mozTransform",h),Ke(xt,"msTransform",h),Ke(xt,"transform",h),Ht=d,Nt=c,Mt=o}e.cancelable&&e.preventDefault()}},_appendGhost:function(){if(!xt){var e=this.options.fallbackOnBody?document.body:$t,t=et(ft,!0,Qt,!0,e),i=this.options;if(Qt){for(Bt=e;"static"===Ke(Bt,"position")&&"none"===Ke(Bt,"transform")&&Bt!==document;)Bt=Bt.parentNode;Bt!==document.body&&Bt!==document.documentElement?(Bt===document&&(Bt=Qe()),t.top+=Bt.scrollTop,t.left+=Bt.scrollLeft):Bt=Qe(),Wt=at(Bt)}We(xt=ft.cloneNode(!0),i.ghostClass,!1),We(xt,i.fallbackClass,!0),We(xt,i.dragClass,!0),Ke(xt,"transition",""),Ke(xt,"transform",""),Ke(xt,"box-sizing","border-box"),Ke(xt,"margin",0),Ke(xt,"top",t.top),Ke(xt,"left",t.left),Ke(xt,"width",t.width),Ke(xt,"height",t.height),Ke(xt,"opacity","0.8"),Ke(xt,"position",Qt?"absolute":"fixed"),Ke(xt,"zIndex","100000"),Ke(xt,"pointerEvents","none"),di.ghost=xt,e.appendChild(xt),Ke(xt,"transform-origin",zt/parseInt(xt.style.width)*100+"% "+Lt/parseInt(xt.style.height)*100+"%")}},_onDragStart:function(e,t){var i=this,s=e.dataTransfer,o=i.options;_t("dragStart",this,{evt:e}),di.eventCanceled?this._onDrop():(_t("setupClone",this),di.eventCanceled||((Dt=ct(ft)).removeAttribute("id"),Dt.draggable=!1,Dt.style["will-change"]="",this._hideClone(),We(Dt,this.options.chosenClass,!1),di.clone=Dt),i.cloneId=ui(function(){_t("clone",i),di.eventCanceled||(i.options.removeCloneOnHide||$t.insertBefore(Dt,ft),i._hideClone(),bt({sortable:i,name:"clone"}))}),!t&&We(ft,o.dragClass,!0),t?(qt=!0,i._loopId=setInterval(i._emulateDragOver,50)):(Be(document,"mouseup",i._onDrop),Be(document,"touchend",i._onDrop),Be(document,"touchcancel",i._onDrop),s&&(s.effectAllowed="move",o.setData&&o.setData.call(i,s,ft)),Fe(document,"drop",i),Ke(ft,"transform","translateZ(0)")),jt=!0,i._dragStartId=ui(i._dragStarted.bind(i,t,e)),Fe(document,"selectstart",i),Vt=!0,window.getSelection().removeAllRanges(),Le&&Ke(document.body,"user-select","none"))},_onDragOver:function(e){var t,i,s,o,a=this.el,r=e.target,n=this.options,l=n.group,d=di.active,c=Pt===l,h=n.sort,p=It||d,g=this,u=!1;if(!Kt){if(void 0!==e.preventDefault&&e.cancelable&&e.preventDefault(),r=Xe(r,n.draggable,a,!0),A("dragOver"),di.eventCanceled)return u;if(ft.contains(e.target)||r.animated&&r.animatingX&&r.animatingY||g._ignoreWhileAnimating===r)return P(!1);if(qt=!1,d&&!n.disabled&&(c?h||(s=yt!==$t):It===this||(this.lastPutMode=Pt.checkPull(this,d,ft,e))&&l.checkPut(this,d,ft,e))){if(o="vertical"===this._getDirection(e,r),t=et(ft),A("dragOverValid"),di.eventCanceled)return u;if(s)return yt=$t,E(),this._hideClone(),A("revert"),di.eventCanceled||(wt?$t.insertBefore(ft,wt):$t.appendChild(ft)),P(!0);var m=st(a,n.draggable);if(!m||function(e,t,i){var s=et(st(i.el,i.options.draggable)),o=ht(i.el,i.options,xt);return t?e.clientX>o.right+10||e.clientY>s.bottom&&e.clientX>s.left:e.clientY>o.bottom+10||e.clientX>s.right&&e.clientY>s.top}(e,o,this)&&!m.animated){if(m===ft)return P(!1);if(m&&a===e.target&&(r=m),r&&(i=et(r)),!1!==ci($t,a,ft,t,r,i,e,!!r))return E(),m&&m.nextSibling?a.insertBefore(ft,m.nextSibling):a.appendChild(ft),yt=a,I(),P(!0)}else if(m&&function(e,t,i){var s=et(it(i.el,0,i.options,!0)),o=ht(i.el,i.options,xt);return t?e.clientX<o.left-10||e.clientY<s.top&&e.clientX<s.right:e.clientY<o.top-10||e.clientY<s.bottom&&e.clientX<s.left}(e,o,this)){var v=it(a,0,n,!0);if(v===ft)return P(!1);if(i=et(r=v),!1!==ci($t,a,ft,t,r,i,e,!1))return E(),a.insertBefore(ft,v),yt=a,I(),P(!0)}else if(r.parentNode===a){i=et(r);var _,b,f,y=ft.parentNode!==a,x=!function(e,t,i){var s=i?e.left:e.top,o=i?e.right:e.bottom,a=i?e.width:e.height,r=i?t.left:t.top,n=i?t.right:t.bottom,l=i?t.width:t.height;return s===r||o===n||s+a/2===r+l/2}(ft.animated&&ft.toRect||t,r.animated&&r.toRect||i,o),$=o?"top":"left",w=tt(r,"top","top")||tt(ft,"top","top"),k=w?w.scrollTop:void 0;if(Ot!==r&&(b=i[$],Zt=!1,Yt=!x&&n.invertSwap||y),_=function(e,t,i,s,o,a,r,n){var l=s?e.clientY:e.clientX,d=s?i.height:i.width,c=s?i.top:i.left,h=s?i.bottom:i.right,p=!1;if(!r)if(n&&Ft<d*o){if(!Zt&&(1===Ut?l>c+d*a/2:l<h-d*a/2)&&(Zt=!0),Zt)p=!0;else if(1===Ut?l<c+Ft:l>h-Ft)return-Ut}else if(l>c+d*(1-o)/2&&l<h-d*(1-o)/2)return function(e){return ot(ft)<ot(e)?1:-1}(t);return(p=p||r)&&(l<c+d*a/2||l>h-d*a/2)?l>c+d/2?1:-1:0}(e,r,i,o,x?1:n.swapThreshold,null==n.invertedSwapThreshold?n.swapThreshold:n.invertedSwapThreshold,Yt,Ot===r),0!==_){var D=ot(ft);do{D-=_,f=yt.children[D]}while(f&&("none"===Ke(f,"display")||f===xt))}if(0===_||f===r)return P(!1);Ot=r,Ut=_;var S=r.nextElementSibling,C=!1,T=ci($t,a,ft,t,r,i,e,C=1===_);if(!1!==T)return 1!==T&&-1!==T||(C=1===T),Kt=!0,setTimeout(pi,30),E(),C&&!S?a.appendChild(ft):r.parentNode.insertBefore(ft,C?S:r),w&&dt(w,0,k-w.scrollTop),yt=ft.parentNode,void 0===b||Yt||(Ft=Math.abs(b-et(r)[$])),I(),P(!0)}if(a.contains(ft))return P(!1)}return!1}function A(n,l){_t(n,g,Ie({evt:e,isOwner:c,axis:o?"vertical":"horizontal",revert:s,dragRect:t,targetRect:i,canSort:h,fromSortable:p,target:r,completed:P,onMove:function(i,s){return ci($t,a,ft,t,i,et(i),e,s)},changed:I},l))}function E(){A("dragOverAnimationCapture"),g.captureAnimationState(),g!==p&&p.captureAnimationState()}function P(t){return A("dragOverCompleted",{insertion:t}),t&&(c?d._hideClone():d._showClone(g),g!==p&&(We(ft,It?It.options.ghostClass:d.options.ghostClass,!1),We(ft,n.ghostClass,!0)),It!==g&&g!==di.active?It=g:g===di.active&&It&&(It=null),p===g&&(g._ignoreWhileAnimating=r),g.animateAll(function(){A("dragOverAnimationComplete"),g._ignoreWhileAnimating=null}),g!==p&&(p.animateAll(),p._ignoreWhileAnimating=null)),(r===ft&&!ft.animated||r===a&&!r.animated)&&(Ot=null),n.dragoverBubble||e.rootEl||r===document||(ft.parentNode[pt]._isOutsideThisEl(e.target),!t&&ni(e)),!n.dragoverBubble&&e.stopPropagation&&e.stopPropagation(),u=!0}function I(){Tt=ot(ft),Et=ot(ft,n.draggable),bt({sortable:g,name:"change",toEl:a,newIndex:Tt,newDraggableIndex:Et,originalEvent:e})}},_ignoreWhileAnimating:null,_offMoveEvents:function(){Be(document,"mousemove",this._onTouchMove),Be(document,"touchmove",this._onTouchMove),Be(document,"pointermove",this._onTouchMove),Be(document,"dragover",ni),Be(document,"mousemove",ni),Be(document,"touchmove",ni)},_offUpEvents:function(){var e=this.el.ownerDocument;Be(e,"mouseup",this._onDrop),Be(e,"touchend",this._onDrop),Be(e,"pointerup",this._onDrop),Be(e,"pointercancel",this._onDrop),Be(e,"touchcancel",this._onDrop),Be(document,"selectstart",this)},_onDrop:function(e){var t=this.el,i=this.options;Tt=ot(ft),Et=ot(ft,i.draggable),_t("drop",this,{evt:e}),yt=ft&&ft.parentNode,Tt=ot(ft),Et=ot(ft,i.draggable),di.eventCanceled||(jt=!1,Yt=!1,Zt=!1,clearInterval(this._loopId),clearTimeout(this._dragStartTimer),mi(this.cloneId),mi(this._dragStartId),this.nativeDraggable&&(Be(document,"drop",this),Be(t,"dragstart",this._onDragStart)),this._offMoveEvents(),this._offUpEvents(),Le&&Ke(document.body,"user-select",""),Ke(ft,"transform",""),e&&(Vt&&(e.cancelable&&e.preventDefault(),!i.dropBubble&&e.stopPropagation()),xt&&xt.parentNode&&xt.parentNode.removeChild(xt),($t===yt||It&&"clone"!==It.lastPutMode)&&Dt&&Dt.parentNode&&Dt.parentNode.removeChild(Dt),ft&&(this.nativeDraggable&&Be(ft,"dragend",this),hi(ft),ft.style["will-change"]="",Vt&&!jt&&We(ft,It?It.options.ghostClass:this.options.ghostClass,!1),We(ft,this.options.chosenClass,!1),bt({sortable:this,name:"unchoose",toEl:yt,newIndex:null,newDraggableIndex:null,originalEvent:e}),$t!==yt?(Tt>=0&&(bt({rootEl:yt,name:"add",toEl:yt,fromEl:$t,originalEvent:e}),bt({sortable:this,name:"remove",toEl:yt,originalEvent:e}),bt({rootEl:yt,name:"sort",toEl:yt,fromEl:$t,originalEvent:e}),bt({sortable:this,name:"sort",toEl:yt,originalEvent:e})),It&&It.save()):Tt!==Ct&&Tt>=0&&(bt({sortable:this,name:"update",toEl:yt,originalEvent:e}),bt({sortable:this,name:"sort",toEl:yt,originalEvent:e})),di.active&&(null!=Tt&&-1!==Tt||(Tt=Ct,Et=At),bt({sortable:this,name:"end",toEl:yt,originalEvent:e}),this.save())))),this._nulling()},_nulling:function(){_t("nulling",this),$t=ft=yt=xt=wt=Dt=kt=St=Rt=Mt=Vt=Tt=Et=Ct=At=Ot=Ut=It=Pt=di.dragged=di.ghost=di.clone=di.active=null;var e=this.el;Gt.forEach(function(t){e.contains(t)&&(t.checked=!0)}),Gt.length=Ht=Nt=0},handleEvent:function(e){switch(e.type){case"drop":case"dragend":this._onDrop(e);break;case"dragenter":case"dragover":ft&&(this._onDragOver(e),function(e){e.dataTransfer&&(e.dataTransfer.dropEffect="move"),e.cancelable&&e.preventDefault()}(e));break;case"selectstart":e.preventDefault()}},toArray:function(){for(var e,t=[],i=this.el.children,s=0,o=i.length,a=this.options;s<o;s++)Xe(e=i[s],a.draggable,this.el,!1)&&t.push(e.getAttribute(a.dataIdAttr)||gi(e));return t},sort:function(e,t){var i={},s=this.el;this.toArray().forEach(function(e,t){var o=s.children[t];Xe(o,this.options.draggable,s,!1)&&(i[e]=o)},this),t&&this.captureAnimationState(),e.forEach(function(e){i[e]&&(s.removeChild(i[e]),s.appendChild(i[e]))}),t&&this.animateAll()},save:function(){var e=this.options.store;e&&e.set&&e.set(this)},closest:function(e,t){return Xe(e,t||this.options.draggable,this.el,!1)},option:function(e,t){var i=this.options;if(void 0===t)return i[e];var s=mt.modifyOption(this,e,t);i[e]=void 0!==s?s:t,"group"===e&&oi(i)},destroy:function(){_t("destroy",this);var e=this.el;e[pt]=null,Be(e,"mousedown",this._onTapStart),Be(e,"touchstart",this._onTapStart),Be(e,"pointerdown",this._onTapStart),this.nativeDraggable&&(Be(e,"dragover",this),Be(e,"dragenter",this)),Array.prototype.forEach.call(e.querySelectorAll("[draggable]"),function(e){e.removeAttribute("draggable")}),this._onDrop(),this._disableDelayedDragEvents(),Xt.splice(Xt.indexOf(this.el),1),this.el=e=null},_hideClone:function(){if(!St){if(_t("hideClone",this),di.eventCanceled)return;Ke(Dt,"display","none"),this.options.removeCloneOnHide&&Dt.parentNode&&Dt.parentNode.removeChild(Dt),St=!0}},_showClone:function(e){if("clone"===e.lastPutMode){if(St){if(_t("showClone",this),di.eventCanceled)return;ft.parentNode!=$t||this.options.group.revertClone?wt?$t.insertBefore(Dt,wt):$t.appendChild(Dt):$t.insertBefore(Dt,ft),this.options.group.revertClone&&this.animate(ft,Dt),Ke(Dt,"display",""),St=!1}}else this._hideClone()}},Jt&&Fe(document,"touchmove",function(e){(di.active||jt)&&e.cancelable&&e.preventDefault()}),di.utils={on:Fe,off:Be,css:Ke,find:Je,is:function(e,t){return!!Xe(e,t,e,!1)},extend:function(e,t){if(e&&t)for(var i in t)t.hasOwnProperty(i)&&(e[i]=t[i]);return e},throttle:lt,closest:Xe,toggleClass:We,clone:ct,index:ot,nextTick:ui,cancelNextTick:mi,detectDirection:si,getChild:it,expando:pt},di.get=function(e){return e[pt]},di.mount=function(){for(var e=arguments.length,t=new Array(e),i=0;i<e;i++)t[i]=arguments[i];t[0].constructor===Array&&(t=t[0]),t.forEach(function(e){if(!e.prototype||!e.prototype.constructor)throw"Sortable: Mounted plugin must be a constructor function, not ".concat({}.toString.call(e));e.utils&&(di.utils=Ie(Ie({},di.utils),e.utils)),mt.mount(e)})},di.create=function(e,t){return new di(e,t)},di.version="1.15.7";var vi,_i,bi,fi,yi,xi,$i=[],wi=!1;function ki(){$i.forEach(function(e){clearInterval(e.pid)}),$i=[]}function Di(){clearInterval(xi)}var Si=lt(function(e,t,i,s){if(t.scroll){var o,a=(e.touches?e.touches[0]:e).clientX,r=(e.touches?e.touches[0]:e).clientY,n=t.scrollSensitivity,l=t.scrollSpeed,d=Qe(),c=!1;_i!==i&&(_i=i,ki(),vi=t.scroll,o=t.scrollFn,!0===vi&&(vi=rt(i,!0)));var h=0,p=vi;do{var g=p,u=et(g),m=u.top,v=u.bottom,_=u.left,b=u.right,f=u.width,y=u.height,x=void 0,$=void 0,w=g.scrollWidth,k=g.scrollHeight,D=Ke(g),S=g.scrollLeft,C=g.scrollTop;g===d?(x=f<w&&("auto"===D.overflowX||"scroll"===D.overflowX||"visible"===D.overflowX),$=y<k&&("auto"===D.overflowY||"scroll"===D.overflowY||"visible"===D.overflowY)):(x=f<w&&("auto"===D.overflowX||"scroll"===D.overflowX),$=y<k&&("auto"===D.overflowY||"scroll"===D.overflowY));var T=x&&(Math.abs(b-a)<=n&&S+f<w)-(Math.abs(_-a)<=n&&!!S),A=$&&(Math.abs(v-r)<=n&&C+y<k)-(Math.abs(m-r)<=n&&!!C);if(!$i[h])for(var E=0;E<=h;E++)$i[E]||($i[E]={});$i[h].vx==T&&$i[h].vy==A&&$i[h].el===g||($i[h].el=g,$i[h].vx=T,$i[h].vy=A,clearInterval($i[h].pid),0==T&&0==A||(c=!0,$i[h].pid=setInterval(function(){s&&0===this.layer&&di.active._onTouchMove(yi);var t=$i[this.layer].vy?$i[this.layer].vy*l:0,i=$i[this.layer].vx?$i[this.layer].vx*l:0;"function"==typeof o&&"continue"!==o.call(di.dragged.parentNode[pt],i,t,e,yi,$i[this.layer].el)||dt($i[this.layer].el,i,t)}.bind({layer:h}),24))),h++}while(t.bubbleScroll&&p!==d&&(p=rt(p,!1)));wi=c}},30),Ci=function(e){var t=e.originalEvent,i=e.putSortable,s=e.dragEl,o=e.activeSortable,a=e.dispatchSortableEvent,r=e.hideGhostForTarget,n=e.unhideGhostForTarget;if(t){var l=i||o;r();var d=t.changedTouches&&t.changedTouches.length?t.changedTouches[0]:t,c=document.elementFromPoint(d.clientX,d.clientY);n(),l&&!l.el.contains(c)&&(a("spill"),this.onSpill({dragEl:s,putSortable:i}))}};function Ti(){}function Ai(){}Ti.prototype={startIndex:null,dragStart:function(e){var t=e.oldDraggableIndex;this.startIndex=t},onSpill:function(e){var t=e.dragEl,i=e.putSortable;this.sortable.captureAnimationState(),i&&i.captureAnimationState();var s=it(this.sortable.el,this.startIndex,this.options);s?this.sortable.el.insertBefore(t,s):this.sortable.el.appendChild(t),this.sortable.animateAll(),i&&i.animateAll()},drop:Ci},Ee(Ti,{pluginName:"revertOnSpill"}),Ai.prototype={onSpill:function(e){var t=e.dragEl,i=e.putSortable||this.sortable;i.captureAnimationState(),t.parentNode&&t.parentNode.removeChild(t),i.animateAll()},drop:Ci},Ee(Ai,{pluginName:"removeOnSpill"}),di.mount(new function(){function e(){for(var e in this.defaults={scroll:!0,forceAutoScrollFallback:!1,scrollSensitivity:30,scrollSpeed:10,bubbleScroll:!0},this)"_"===e.charAt(0)&&"function"==typeof this[e]&&(this[e]=this[e].bind(this))}return e.prototype={dragStarted:function(e){var t=e.originalEvent;this.sortable.nativeDraggable?Fe(document,"dragover",this._handleAutoScroll):this.options.supportPointer?Fe(document,"pointermove",this._handleFallbackAutoScroll):t.touches?Fe(document,"touchmove",this._handleFallbackAutoScroll):Fe(document,"mousemove",this._handleFallbackAutoScroll)},dragOverCompleted:function(e){var t=e.originalEvent;this.options.dragOverBubble||t.rootEl||this._handleAutoScroll(t)},drop:function(){this.sortable.nativeDraggable?Be(document,"dragover",this._handleAutoScroll):(Be(document,"pointermove",this._handleFallbackAutoScroll),Be(document,"touchmove",this._handleFallbackAutoScroll),Be(document,"mousemove",this._handleFallbackAutoScroll)),Di(),ki(),clearTimeout(Ze),Ze=void 0},nulling:function(){yi=_i=vi=wi=xi=bi=fi=null,$i.length=0},_handleFallbackAutoScroll:function(e){this._handleAutoScroll(e,!0)},_handleAutoScroll:function(e,t){var i=this,s=(e.touches?e.touches[0]:e).clientX,o=(e.touches?e.touches[0]:e).clientY,a=document.elementFromPoint(s,o);if(yi=e,t||this.options.forceAutoScrollFallback||Ne||He||Le){Si(e,this.options,a,t);var r=rt(a,!0);!wi||xi&&s===bi&&o===fi||(xi&&Di(),xi=setInterval(function(){var a=rt(document.elementFromPoint(s,o),!0);a!==r&&(r=a,ki()),Si(e,i.options,a,t)},10),bi=s,fi=o)}else{if(!this.options.bubbleScroll||rt(a,!0)===Qe())return void ki();Si(e,this.options,rt(a,!1),!1)}}},Ee(e,{pluginName:"scroll",initializeByDefault:!0})}),di.mount(Ai,Ti);const Ei=r`
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
`;let Pi=class extends ne{constructor(){super(...arguments),this.color="green",this.count=0}render(){if(this.count<1)return B``;const e=this.count>=10;return B`<span
            class="dot badge ${this.color} ${e?"multi-digit":""}"
            ><span class="digit">${this.count}</span></span
        >`}};Pi.styles=r`
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
           dot for count 1 existed through v0.6.1; retired on the v0.6.3
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
        }
        /* A digit glyph has no descender, so flex-centring the line box leaves
           the number riding ~0.5px above the badge's true centre. Nudge just
           the digit down half a pixel so it sits dead-centre in the circle. */
        .dot.badge .digit {
            display: block;
            transform: translateY(0.5px);
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
    `,e([he({type:String})],Pi.prototype,"color",void 0),e([he({type:Number})],Pi.prototype,"count",void 0),Pi=e([ue("ir-count-dot")],Pi);let Ii=class extends ne{constructor(){super(...arguments),this.templateName="",this.command=null,this.busy=!1,this.actionLabel=null,this.hasTrigger=!1,this.triggerCount=0,this.showActionMapping=!0,this._editingName=!1,this._draftName=""}_commandLabel(){const e=this.command;return e.protocol&&e.code?`${e.protocol}: ${e.code}`:e.raw_timings?.length?`RAW: ${e.raw_timings.length} timings`:e.protocol??"IR"}_prontoSlArray(e){const t=e.trim().split(/\s+/);if(t.length<6)return null;const i=parseInt(t[2],16)+parseInt(t[3],16),s=t.slice(4);if(s.length<2*i)return null;const o=[];for(let e=0;e<2*i;e++){const t=parseInt(s[e],16);o.push(t>=48)}return o.length>0?o:null}_renderDiamonds(){const e=this.command;if(!e||"PRONTO"!==e.protocol?.toUpperCase()||!e.code)return null;const t=this._prontoSlArray(e.code);return t?B`<span class="diamonds">${t.map(e=>e?B`<span class="diamond long">◆</span>`:B`<span class="diamond short">◇</span>`)}</span>`:null}_emit(e,t){const i=t?.currentTarget?.getBoundingClientRect()??null;this.dispatchEvent(new CustomEvent(e,{detail:{templateName:this.templateName,command:this.command,buttonRect:i},bubbles:!0,composed:!0}))}_startRename(e){this.command&&!this.busy&&(e.stopPropagation(),this._draftName=this.command.name,this._editingName=!0,this.updateComplete.then(()=>{const e=this.shadowRoot?.querySelector(".name-input");e?.focus(),e?.select()}))}_commitRename(){if(!this._editingName)return;const e=this._draftName.trim();this._editingName=!1,this.command&&e&&e!==this.command.name&&this.dispatchEvent(new CustomEvent("rename-command",{detail:{command:this.command,name:e},bubbles:!0,composed:!0}))}_onRenameKeydown(e){"Enter"===e.key?(e.preventDefault(),this._commitRename()):"Escape"===e.key&&(this._editingName=!1)}render(){const e=null!==this.command,t=e?this._renderDiamonds():null;return B`
            <div class="row" data-learned=${e?"true":"false"}>
                <div class="status" aria-hidden="true">
                    <slot name="status"></slot>
                </div>
                <div class="info">
                    <div class="name">
                        ${e?this._editingName?B`<input
                                      class="name-input"
                                      type="text"
                                      .value=${this._draftName}
                                      @input=${e=>this._draftName=e.target.value}
                                      @keydown=${this._onRenameKeydown}
                                      @blur=${this._commitRename}
                                  />`:B`<span
                                      class="editable-name"
                                      title="Click to rename"
                                      @click=${this._startRename}
                                      >${this.templateName}<span class="rename-pencil"
                                          >&#9998;</span
                                      ></span
                                  >`:B`${this.templateName}`}
                        ${e&&this.command?.decoded_fingerprint?B`<button
                                  class="tx-pill ${this.command.tx_force_raw?"tx-raw-on":""}"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("toggle-tx-raw")}
                                  title=${this.command.tx_force_raw?"Replaying the captured Pronto. Click to transmit clean decoded packet timings instead.":"Transmitting clean decoded packet timings. Click to replay the captured Pronto instead."}
                              >${this.command.tx_force_raw?"PRONTO":this.command.decoded_protocol??"AUTO"}</button>`:""}
                        ${e&&this.command&&this.command.send_count>1?B`<span
                                  class="repeat-indicator"
                                  title="Sends this command ${this.command.send_count} times"
                                  ><ha-svg-icon
                                      .path=${"M17,17H7V14L3,18L7,22V19H19V13H17M7,7H17V10L21,6L17,2V5H5V11H7V7Z"}
                                  ></ha-svg-icon
                                  >${this.command.send_count}</span
                              >`:""}
                        ${e&&this.command&&this.command.repeat_count>1&&this.command.decoded_protocol&&!this.command.tx_force_raw?B`<span
                                  class="ditto-indicator"
                                  title="Appends ${this.command.repeat_count} NEC dittos"
                                  ><ha-svg-icon
                                      .path=${"M16,12A2,2 0 0,1 18,10A2,2 0 0,1 20,12A2,2 0 0,1 18,14A2,2 0 0,1 16,12M10,12A2,2 0 0,1 12,10A2,2 0 0,1 14,12A2,2 0 0,1 12,14A2,2 0 0,1 10,12M4,12A2,2 0 0,1 6,10A2,2 0 0,1 8,12A2,2 0 0,1 6,14A2,2 0 0,1 4,12Z"}
                                  ></ha-svg-icon
                                  >${this.command.repeat_count}</span
                              >`:""}
                    </div>
                    <div class="meta">
                        ${t||(e?B`${this._commandLabel()}`:B`<span class="muted">Not yet learned</span>`)}
                    </div>
                </div>
                <div class="actions">
                    ${e?B`
                              <button
                                  class="icon-btn edit-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("edit-command")}
                                  title="View or edit code"
                              ><ha-svg-icon
                                      class="edit-glyph"
                                      .path=${"M19,21H8V7H19M19,5H8A2,2 0 0,0 6,7V21A2,2 0 0,0 8,23H19A2,2 0 0,0 21,21V7A2,2 0 0,0 19,5M16,1H4A2,2 0 0,0 2,3V17H4V3H16V1Z"}
                                  ></ha-svg-icon></button>
                              ${this.showActionMapping?B`<button
                                  class="action-btn badge-btn"
                                  ?data-mapped=${!!this.actionLabel}
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("map-action")}
                                  title="Assign action mapping"
                              >${this.actionLabel||"ACTIONS"}</button>`:""}
                              <button
                                  class="action-btn test-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("test")}
                              >Test</button>
                              <button
                                  class="action-btn trigger-btn"
                                  ?disabled=${this.busy}
                                  @click=${e=>this._emit("toggle-trigger",e)}
                                  title=${this.hasTrigger?"Edit trigger":"Create trigger"}
                              >Trigger<ir-count-dot
                                      color="yellow"
                                      .count=${this.triggerCount||(this.hasTrigger?1:0)}
                                  ></ir-count-dot></button>
                              <button
                                  class="action-btn delete-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("delete")}
                              >Delete</button>
                          `:B`
                              <button
                                  class="action-btn learn-btn"
                                  ?disabled=${this.busy}
                                  @click=${()=>this._emit("learn")}
                              >Learn</button>
                          `}
                </div>
            </div>
        `}};Ii.styles=r`
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
    `,e([he({attribute:!1})],Ii.prototype,"templateName",void 0),e([he({attribute:!1})],Ii.prototype,"command",void 0),e([he({type:Boolean})],Ii.prototype,"busy",void 0),e([he({attribute:!1})],Ii.prototype,"actionLabel",void 0),e([he({type:Boolean})],Ii.prototype,"hasTrigger",void 0),e([he({type:Number})],Ii.prototype,"triggerCount",void 0),e([he({type:Boolean})],Ii.prototype,"showActionMapping",void 0),e([pe()],Ii.prototype,"_editingName",void 0),e([pe()],Ii.prototype,"_draftName",void 0),Ii=e([ue("ir-command-row")],Ii);let Ri=class extends ne{constructor(){super(...arguments),this.commandName="",this.timeout=15,this._phase="listening",this._result=null,this._duplicate=null,this._error=null,this._timeRemaining=0,this._sessionId=null,this._unsubscribe=null,this._countdown=null}connectedCallback(){super.connectedCallback(),this._beginCapture()}disconnectedCallback(){super.disconnectedCallback(),this._stopCountdown(),this._unsubscribe&&(this._unsubscribe(),this._unsubscribe=null)}async _beginCapture(){this._phase="listening",this._result=null,this._duplicate=null,this._error=null,this._timeRemaining=this.timeout,this._startCountdown();try{const{session:e,unsubscribe:t}=await this.api.startCapture(this.device.id,this.timeout,e=>this._onCaptureEvent(e));this._sessionId=e.session_id,this._unsubscribe=t}catch(e){this._stopCountdown(),this._error=e.message,this._phase="error"}}_onCaptureEvent(e){switch(e.type){case"capture_listening":this._phase="listening";break;case"capture_received":this._stopCountdown(),this._result=e.result,e.duplicate_of?(this._duplicate=e.duplicate_of,this._phase="duplicate"):this._phase="captured";break;case"capture_timeout":this._stopCountdown(),this._phase="timeout";break;case"capture_error":this._stopCountdown(),this._error=e.error,this._phase="error";break;case"capture_cancelled":this._stopCountdown(),this._close()}}_startCountdown(){this._stopCountdown();const e=Date.now();this._countdown=window.setInterval(()=>{const t=(Date.now()-e)/1e3;this._timeRemaining=Math.max(0,Math.ceil(this.timeout-t)),this._timeRemaining<=0&&this._stopCountdown()},250)}_stopCountdown(){null!==this._countdown&&(clearInterval(this._countdown),this._countdown=null)}async _cancel(){if(this._sessionId)try{await this.api.cancelCapture(this._sessionId)}catch{}this._close()}async _testCommand(){if(!this._sessionId)return;const e=`__hair_test_${Date.now()}`;try{const t=await this.api.saveCapturedCommand({device_id:this.device.id,session_id:this._sessionId,command_name:e});await this.api.sendCommand(this.device.id,t.id),await this.api.deleteCommand(this.device.id,t.id)}catch(e){this._error=e.message,this._phase="error"}}async _save(e){if(this._sessionId)try{await this.api.saveCapturedCommand({device_id:this.device.id,session_id:this._sessionId,command_name:this.commandName}),this.dispatchEvent(new CustomEvent("command-saved",{detail:{saveAndNext:e,commandName:this.commandName},bubbles:!0,composed:!0})),this._close()}catch(e){this._error=e.message,this._phase="error"}}async _recapture(){this._unsubscribe&&(await this._unsubscribe(),this._unsubscribe=null),await this._beginCapture()}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_renderListening(){return B`
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
        `}};Ri.styles=r`
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
    `,e([he({attribute:!1})],Ri.prototype,"api",void 0),e([he({attribute:!1})],Ri.prototype,"hass",void 0),e([he({attribute:!1})],Ri.prototype,"device",void 0),e([he({attribute:!1})],Ri.prototype,"commandName",void 0),e([he({attribute:!1})],Ri.prototype,"timeout",void 0),e([pe()],Ri.prototype,"_phase",void 0),e([pe()],Ri.prototype,"_result",void 0),e([pe()],Ri.prototype,"_duplicate",void 0),e([pe()],Ri.prototype,"_error",void 0),e([pe()],Ri.prototype,"_timeRemaining",void 0),e([pe()],Ri.prototype,"_sessionId",void 0),Ri=e([ue("ir-capture-dialog")],Ri);let Mi=class extends ne{constructor(){super(...arguments),this.title="Confirm",this.message="Are you sure?",this.confirmLabel="Confirm",this.cancelLabel="Cancel",this.destructive=!1,this._busy=!1}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_confirm(){this.dispatchEvent(new CustomEvent("confirmed",{bubbles:!0,composed:!0}))}render(){return B`
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
        `}};Mi.styles=r`
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
    `,e([he()],Mi.prototype,"title",void 0),e([he()],Mi.prototype,"message",void 0),e([he()],Mi.prototype,"confirmLabel",void 0),e([he()],Mi.prototype,"cancelLabel",void 0),e([he({type:Boolean})],Mi.prototype,"destructive",void 0),e([pe()],Mi.prototype,"_busy",void 0),Mi=e([ue("ir-confirm-dialog")],Mi);let Hi=class extends ne{constructor(){super(...arguments),this.value=[],this.disabled=!1,this.excludeEntityIds=[],this._didAutoSelect=!1,this._receiverIds=new Set,this._receiversLoaded=!1}updated(e){if(super.updated(e),e.has("api")&&this.api&&!this._receiversLoaded&&(this._receiversLoaded=!0,this._loadReceivers()),!this._didAutoSelect)if(this.value.length>0)this._didAutoSelect=!0;else{const e=this._getEmitters();1===e.length&&(this._didAutoSelect=!0,this._fireChange([e[0].entity_id]))}}async _loadReceivers(){if(this.api)try{const e=await this.api.listReceivers();this._receiverIds=new Set(e.map(e=>e.entity_id))}catch{this._receiverIds=new Set}}_getEmitters(){const e=this.hass?.states??{},t=new Set(this.excludeEntityIds),i=[];for(const[s,o]of Object.entries(e))!s.startsWith("infrared.")||t.has(s)||this._receiverIds.has(s)||o.attributes.hair_observer||i.push({entity_id:s,name:o.attributes.friendly_name??s});return i}_emitterName(e){const t=this.hass?.states?.[e];return t?.attributes?.friendly_name??e}_onAdd(e){const t=e.target,i=t.value;i&&(t.value="",this.value.includes(i)||this._fireChange([...this.value,i]))}_onRemove(e){this._fireChange(this.value.filter(t=>t!==e))}_fireChange(e){this.value=e,this.dispatchEvent(new CustomEvent("emitters-changed",{detail:{value:e},bubbles:!0,composed:!0}))}render(){const e=this._getEmitters(),t=e.filter(e=>!this.value.includes(e.entity_id));return B`
            <label>IR emitters</label>

            ${this.value.length>0?B`
                      <div class="chips">
                          ${this.value.map(e=>B`
                                  <span class="chip">
                                      <span class="chip-name">${this._emitterName(e)}</span>
                                      ${this.disabled?"":B`<button
                                                class="chip-remove"
                                                @click=${()=>this._onRemove(e)}
                                                title="Remove"
                                            >&times;</button>`}
                                  </span>
                              `)}
                      </div>
                  `:""}

            ${0===e.length?B`<div class="no-emitters">No IR emitters found.</div>`:t.length>0?B`
                        <select
                            @change=${this._onAdd}
                            ?disabled=${this.disabled}
                        >
                            <option value="">+ Add emitter...</option>
                            ${t.map(e=>B`
                                    <option value=${e.entity_id}>
                                        ${e.name}
                                    </option>
                                `)}
                        </select>
                    `:this.value.length>0?B`<div class="all-selected">All emitters selected.</div>`:""}
        `}};Hi.styles=r`
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
    `,e([he({attribute:!1})],Hi.prototype,"hass",void 0),e([he({attribute:!1})],Hi.prototype,"api",void 0),e([he({attribute:!1})],Hi.prototype,"value",void 0),e([he({type:Boolean})],Hi.prototype,"disabled",void 0),e([he({attribute:!1})],Hi.prototype,"excludeEntityIds",void 0),e([pe()],Hi.prototype,"_didAutoSelect",void 0),e([pe()],Hi.prototype,"_receiverIds",void 0),Hi=e([ue("ir-emitter-picker")],Hi);const Ni=[3e4,33e3,36e3,38e3,4e4,56e3],zi=e=>Ni.reduce((t,i)=>Math.abs(i-e)<Math.abs(t-e)?i:t);let Li=class extends ne{constructor(){super(...arguments),this.signalId=null,this.commandId=null,this.initialPronto="",this.initialAlias="",this.initialSendCount=1,this.initialDitto=1,this.initialObservedRepeatCount=0,this.initialTxForceRaw=!1,this.initialDecodedProtocol=null,this.hasTrigger=!1,this.allowSnap=!1,this._pronto="",this._alias="",this._sendCount=1,this._ditto=1,this._busy=!1,this._error=null,this._validation=null,this._copyHint=null,this._snapping=!1,this._snapFlash=!1,this._debounce=null}get _isCommand(){return null!==this.commandId}get _isEdit(){return null!==this.signalId||null!==this.commandId}get _dirty(){return this._pronto!==this.initialPronto||this._alias!==this.initialAlias||this._sendCount!==this.initialSendCount||this._ditto!==this.initialDitto}get _canSave(){return!this._busy&&!0===this._validation?.valid&&(!this._isEdit||this._dirty)}get _dittoCountDisabled(){return this._isCommand?!this.initialDecodedProtocol||!!this.initialTxForceRaw:!this._pronto.trim()||null===this._validation||!this._validation.recognized_protocol}get _dittoDisabledTooltip(){return this._isCommand&&this.initialDecodedProtocol&&this.initialTxForceRaw?"Ditto count applies when the command transmits as NEC. Toggle the pill to NEC to enable.":"Ditto count applies to decoded signals (NEC today). Raw Pronto codes transmit as captured."}firstUpdated(){this._pronto=this.initialPronto,this._alias=this.initialAlias,this._sendCount=this.initialSendCount,this._ditto=this.initialDitto,this._pronto.trim()&&this._validate()}updated(){const e=this.shadowRoot?.querySelector("textarea");if(!e)return;const t=Math.round(.45*window.innerHeight);e.style.height="0px";const i=Math.min(Math.max(e.scrollHeight+2,64),t);e.style.height=`${i}px`}disconnectedCallback(){super.disconnectedCallback(),null!==this._debounce&&clearTimeout(this._debounce)}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_onSendCountInput(e){const t=parseInt(e.target.value,10);this._sendCount=Number.isNaN(t)?1:Math.max(1,Math.min(t,10))}_onDittoInput(e){const t=parseInt(e.target.value,10);this._ditto=Number.isNaN(t)?0:Math.max(0,Math.min(t,20))}_onProntoInput(e){this._pronto=e.target.value,null!==this._debounce&&clearTimeout(this._debounce),this._pronto.trim()?this._debounce=setTimeout(()=>{this._validate()},250):this._validation=null}_onKeydown(e){"Enter"!==e.key||e.shiftKey||(e.preventDefault(),this._canSave&&this._save())}async _validate(){try{this._validation=await this.api.validatePronto(this._pronto)}catch{this._validation=null}}_slPreview(){const e=this._validation?.normalized;if(!e)return null;const t=e.split(" ").map(e=>parseInt(e,16));if(t.length<5||t.some(e=>Number.isNaN(e)))return null;const i=[];for(const e of t.slice(4)){if(e>=1024)break;i.push(e<48?"S":"L")}return i.length?i:null}async _save(){if(!this._canSave)return;this._busy=!0,this._error=null;const e=this._dittoCountDisabled?void 0:this._ditto;try{if(this._isCommand){const t=await this.api.updateCommand({device_id:this.deviceId,command_id:this.commandId,name:this._alias.trim(),pronto:this._pronto,send_count:this._sendCount,repeat_count:e});this.dispatchEvent(new CustomEvent("command-edited",{detail:t,bubbles:!0,composed:!0}))}else if(null!==this.signalId){const t=await this.api.editSignalPronto({device_id:this.deviceId,signal_id:this.signalId,pronto:this._pronto,alias:this._alias.trim(),send_count:this._sendCount,repeat_count:e});this.dispatchEvent(new CustomEvent("signal-edited",{detail:t,bubbles:!0,composed:!0}))}else{const t=await this.api.createSignal({device_id:this.deviceId,pronto:this._pronto,alias:this._alias.trim()||void 0,send_count:this._sendCount,repeat_count:e});this.dispatchEvent(new CustomEvent("signal-created",{detail:t.signal,bubbles:!0,composed:!0}))}}catch(e){this._error=e.message}finally{this._busy=!1}}async _selectCode(){const e=this.shadowRoot?.querySelector("textarea");e&&(e.focus(),e.select());let t=!1;try{window.isSecureContext&&navigator.clipboard&&(await navigator.clipboard.writeText(this._pronto),t=!0)}catch{t=!1}this._copyHint=t?"Copied":"Press Cmd/Ctrl+C",setTimeout(()=>{this._copyHint=null},2e3)}_renderFeedback(){const e=this._validation;if(!e)return"";const t=this._slPreview();return B`
            <div class="feedback">
                <div class="status ${e.valid?"ok":"bad"}">
                    <span class="mark">${e.valid?"✓":"✗"}</span>
                    ${e.valid?"Valid Pronto code":"Not valid yet"}
                </div>
                ${e.valid?B`
                          <div class="metrics">
                              ${null!==e.frequency_khz?B`<span>${e.frequency_khz} kHz</span>`:""}
                              ${null!==e.burst_pair_count?B`<span
                                        >${e.burst_pair_count} burst
                                        ${1===e.burst_pair_count?"pair":"pairs"}</span
                                    >`:""}
                              ${e.recognized_protocol?B`<span class="recognized"
                                        >Recognized as ${e.recognized_protocol}</span
                                    >`:""}
                          </div>
                          ${t?B`<div class="diamonds">
                                    ${t.map(e=>"L"===e?B`<span class="diamond long">◆</span>`:B`<span class="diamond short">◇</span>`)}
                                </div>`:""}
                      `:""}
                ${e.errors.map(e=>B`<div class="msg err">${e}</div>`)}
                ${e.warnings.map(e=>B`<div class="msg warn">${e}</div>`)}
            </div>
        `}get _carrierHz(){const e=this._validation?.valid?this._validation.frequency_khz:null;return null!=e?Math.round(1e3*e):null}get _showSnap(){if(!this.allowSnap)return!1;const e=this._carrierHz;return null!=e&&!(e=>Math.abs(e-zi(e))<=500)(e)}async _snap(e){this._snapping=!0,this._error=null;try{const t=await this.api.snapPreview({pronto:this._pronto,target_frequency:e});this._pronto=t.pronto,await this._validate(),this._snapFlash=!0,setTimeout(()=>{this._snapFlash=!1},700)}catch(e){this._error=e.message}finally{this._snapping=!1}}_renderSnap(){if(!this._showSnap)return"";const e=this._carrierHz,t=zi(e),i=(e/1e3).toFixed(1),s=(t/1e3).toFixed(0);return B`
            <div class="snap-notice">
                <div class="snap-text">
                    Carrier is ${i} kHz, off the IR standards. Some
                    receivers reject it.
                </div>
                <button
                    class="snap-btn"
                    ?disabled=${this._snapping}
                    @click=${()=>this._snap(t)}
                >
                    ${this._snapping?"Snapping...":`Snap to ${s} kHz`}
                </button>
            </div>
        `}render(){const e=this._isCommand?"Edit command":this._isEdit?"Edit signal":"Create signal",t=this._isEdit?this._busy?"Saving...":"Save":this._busy?"Creating...":"Create",i=this._isEdit&&this.hasTrigger&&this._dirty,s=this._isCommand?"This command has a trigger that will automatically re-point.":"This signal has a trigger that will automatically re-point.",o=this._isCommand?"Command name":"Alias"+(this._isEdit?"":" (optional)");return B`
            <ha-dialog
                open
                heading=${e}
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <div class="field">
                    <label>Pronto code</label>
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
                        ${this._pronto.trim()?B`
                                  ${this._copyHint?B`<span class="copy-flash"
                                            >${this._copyHint}</span
                                        >`:""}
                                  <button
                                      class="copy-icon"
                                      title="Select all (then Cmd/Ctrl+C)"
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
                    <label>${o}</label>
                    <input
                        type="text"
                        .value=${this._alias}
                        placeholder="e.g. Power"
                        @input=${e=>this._alias=e.target.value}
                        @keydown=${this._onKeydown}
                    />
                </div>

                <div class="field tx-knobs">
                    <div class="knob">
                        <label>Send times</label>
                        <input
                            class="num-input"
                            type="number"
                            min="1"
                            max="10"
                            .value=${String(this._sendCount)}
                            title="Transmit the whole command this many times as independent presses, for devices that need a repeat to register."
                            @input=${this._onSendCountInput}
                            @keydown=${this._onKeydown}
                        />
                    </div>
                    ${this._dittoCountDisabled?"":B`<div class="knob">
                              <label>Ditto count</label>
                              <input
                                  class="num-input"
                                  type="number"
                                  min="0"
                                  max="20"
                                  .value=${String(this._ditto)}
                                  title='Append repeat frames after the main frame. Some strict receivers, notably commercial audio gear, need at least one to register the command.'
                                  @input=${this._onDittoInput}
                                  @keydown=${this._onKeydown}
                              />
                          </div>`}
                </div>
                ${this.initialObservedRepeatCount>0?B`<div class="observed-hint">
                          Observed at capture:
                          ${this.initialObservedRepeatCount}
                          ${1===this.initialObservedRepeatCount?"ditto":"dittos"}
                      </div>`:""}

                ${i?B`<div class="note">${s}</div>`:""}

                <div class="dialog-actions">
                    <span class="spacer"></span>
                    <button
                        class="action-btn cancel-btn"
                        @click=${this._close}
                        ?disabled=${this._busy}
                    >
                        Cancel
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
        `}};Li.styles=r`
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
        .dialog-actions {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-top: 20px;
            padding-top: 16px;
            border-top: 1px solid var(--divider-color);
        }
        .spacer {
            flex: 1;
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
        .cancel-btn,
        .copy-btn {
            background: transparent;
            color: var(--secondary-text-color);
        }
        .cancel-btn:hover:not(:disabled),
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
    `,e([he({attribute:!1})],Li.prototype,"api",void 0),e([he({attribute:!1})],Li.prototype,"deviceId",void 0),e([he({attribute:!1})],Li.prototype,"signalId",void 0),e([he({attribute:!1})],Li.prototype,"commandId",void 0),e([he({attribute:!1})],Li.prototype,"initialPronto",void 0),e([he({attribute:!1})],Li.prototype,"initialAlias",void 0),e([he({attribute:!1})],Li.prototype,"initialSendCount",void 0),e([he({attribute:!1})],Li.prototype,"initialDitto",void 0),e([he({attribute:!1})],Li.prototype,"initialObservedRepeatCount",void 0),e([he({attribute:!1})],Li.prototype,"initialTxForceRaw",void 0),e([he({attribute:!1})],Li.prototype,"initialDecodedProtocol",void 0),e([he({type:Boolean})],Li.prototype,"hasTrigger",void 0),e([he({type:Boolean})],Li.prototype,"allowSnap",void 0),e([pe()],Li.prototype,"_pronto",void 0),e([pe()],Li.prototype,"_alias",void 0),e([pe()],Li.prototype,"_sendCount",void 0),e([pe()],Li.prototype,"_ditto",void 0),e([pe()],Li.prototype,"_busy",void 0),e([pe()],Li.prototype,"_error",void 0),e([pe()],Li.prototype,"_validation",void 0),e([pe()],Li.prototype,"_copyHint",void 0),e([pe()],Li.prototype,"_snapping",void 0),e([pe()],Li.prototype,"_snapFlash",void 0),Li=e([ue("ir-signal-editor")],Li);let Vi=class extends ne{constructor(){super(...arguments),this.value=[],this.disabled=!1,this._receivers=[],this._receiversLoaded=!1}updated(e){super.updated(e),e.has("api")&&this.api&&!this._receiversLoaded&&(this._receiversLoaded=!0,this._loadReceivers())}async _loadReceivers(){if(this.api)try{this._receivers=await this.api.listReceivers()}catch{this._receivers=[]}}_receiverName(e){const t=this._receivers.find(t=>t.entity_id===e);return t?.name??e}_onAdd(e){const t=e.target,i=t.value;i&&(t.value="",this.value.includes(i)||this._fireChange([...this.value,i]))}_onRemove(e){this._fireChange(this.value.filter(t=>t!==e))}_fireChange(e){this.value=e,this.dispatchEvent(new CustomEvent("receivers-changed",{detail:{value:e},bubbles:!0,composed:!0}))}render(){const e=this._receivers.filter(e=>!this.value.includes(e.entity_id));return B`
            <label>Via receiver(s):</label>

            ${this.value.length>0?B`
                      <div class="chips">
                          ${this.value.map(e=>B`
                                  <span class="chip">
                                      <span class="chip-name"
                                          >${this._receiverName(e)}</span
                                      >
                                      ${this.disabled?"":B`<button
                                                class="chip-remove"
                                                @click=${()=>this._onRemove(e)}
                                                title="Remove"
                                            >
                                                &times;
                                            </button>`}
                                  </span>
                              `)}
                      </div>
                  `:""}

            ${0===this._receivers.length?B`<div class="no-receivers">No IR receivers found.</div>`:e.length>0?B`
                        <select @change=${this._onAdd} ?disabled=${this.disabled}>
                            <option value="">+ Add receiver...</option>
                            ${e.map(e=>B`
                                    <option value=${e.entity_id}>
                                        ${e.name}
                                    </option>
                                `)}
                        </select>
                    `:B`<div class="all-selected">All receivers selected.</div>`}
        `}};Vi.styles=r`
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
    `,e([he({attribute:!1})],Vi.prototype,"api",void 0),e([he({attribute:!1})],Vi.prototype,"value",void 0),e([he({type:Boolean})],Vi.prototype,"disabled",void 0),e([pe()],Vi.prototype,"_receivers",void 0),Vi=e([ue("ir-receiver-picker")],Vi);let Oi=class extends ne{constructor(){super(...arguments),this.signalFingerprint="",this.protocol=null,this.code=null,this.slPattern=null,this.alias=null,this.byteHash=null,this.decodedFingerprint=null,this.sourceDeviceId=null,this.sourceCommandId=null,this.trigger=null,this.mirrorContext=!1,this._name="",this._minHits=1,this._receiverIds=[],this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this.trigger&&(this._name=this.trigger.name,this._minHits=this.trigger.min_hits,this._receiverIds=[...this.trigger.receiver_entity_ids??[]])}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _save(){const e=this._name.trim();if(e){this._busy=!0,this._error=null;try{let t;if(this.trigger)t=await this.api.updateTrigger(this.trigger.id,{name:e,min_hits:this._minHits,receiver_entity_ids:this._receiverIds});else{const i={name:e,protocol:this.protocol,code:this.code,min_hits:this._minHits,source_device_id:this.sourceDeviceId,source_command_id:this.sourceCommandId,receiver_entity_ids:this._receiverIds};this.signalFingerprint&&(i.signal_fingerprint=this.signalFingerprint),this.byteHash&&(i.byte_hash=this.byteHash),this.decodedFingerprint&&(i.decoded_fingerprint=this.decodedFingerprint),t=await this.api.createTrigger(i)}this.dispatchEvent(new CustomEvent("trigger-saved",{detail:t,bubbles:!0,composed:!0}))}catch(e){this._error=e.message??"Save failed"}finally{this._busy=!1}}else this._error="Name is required."}_emitDelete(){this.trigger&&this.dispatchEvent(new CustomEvent("trigger-delete",{detail:{triggerId:this.trigger.id},bubbles:!0,composed:!0}))}_prontoSlArray(e){const t=e.trim().split(/\s+/);if(t.length<6)return null;const i=parseInt(t[2],16)+parseInt(t[3],16),s=t.slice(4);if(s.length<2*i)return null;const o=[];for(let e=0;e<2*i;e++){const t=parseInt(s[e],16);o.push(t>=48)}return o.length>0?o:null}_renderSignalInfo(){const e=!!this.trigger;if(!e&&this.alias)return B`<span class="alias-inline"
                ><span class="alias-tag">alias</span
                ><span class="alias-name">${this.alias}</span></span
            >`;const t=e?null:this.slPattern;if(t)return B`<span class="diamonds">${[...t].map(e=>"L"===e?B`<span class="diamond long">&#9670;</span>`:B`<span class="diamond short">&#9671;</span>`)}</span>`;const i=e?this.trigger.code:this.code,s=e?this.trigger.protocol:this.protocol;if("PRONTO"===s?.toUpperCase()&&i){const e=this._prontoSlArray(i);if(e)return B`<span class="diamonds">${e.map(e=>e?B`<span class="diamond long">&#9670;</span>`:B`<span class="diamond short">&#9671;</span>`)}</span>`}return B`<span class="proto">Trigger Event</span>`}render(){const e=!!this.trigger;return B`
            <div class="overlay" @click=${this._close}>
                <div class="dialog" @click=${e=>e.stopPropagation()}>
                    <h3 class="heading">
                        ${e?"Edit Trigger":"Create Trigger"}
                    </h3>

                    <!-- Signal info (read-only) -->
                    <div class="signal-info">
                        ${this._renderSignalInfo()}
                    </div>

                    ${this.mirrorContext?B`<p class="field-hint scope-hint">
                              Fires when this signal arrives from outside
                              Home Assistant (a physical remote or another
                              app), never on the house's own sends.
                          </p>`:""}

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

                    <!-- Receiver scope -->
                    <div class="receiver-field">
                        <ir-receiver-picker
                            .api=${this.api}
                            .value=${this._receiverIds}
                            ?disabled=${this._busy}
                            @receivers-changed=${e=>{this._receiverIds=e.detail.value}}
                        ></ir-receiver-picker>
                        <p class="field-hint scope-hint">
                            Fires once per press, regardless of how many scoped
                            receivers observe the signal.
                        </p>
                    </div>

                    ${this._error?B`<p class="error">${this._error}</p>`:""}

                    <div class="actions">
                        ${e?B`<button
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
        `}};Oi.styles=r`
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
    `,e([he({attribute:!1})],Oi.prototype,"api",void 0),e([he()],Oi.prototype,"signalFingerprint",void 0),e([he()],Oi.prototype,"protocol",void 0),e([he()],Oi.prototype,"code",void 0),e([he()],Oi.prototype,"slPattern",void 0),e([he()],Oi.prototype,"alias",void 0),e([he()],Oi.prototype,"byteHash",void 0),e([he()],Oi.prototype,"decodedFingerprint",void 0),e([he()],Oi.prototype,"sourceDeviceId",void 0),e([he()],Oi.prototype,"sourceCommandId",void 0),e([he({attribute:!1})],Oi.prototype,"trigger",void 0),e([he({type:Boolean})],Oi.prototype,"mirrorContext",void 0),e([pe()],Oi.prototype,"_name",void 0),e([pe()],Oi.prototype,"_minHits",void 0),e([pe()],Oi.prototype,"_receiverIds",void 0),e([pe()],Oi.prototype,"_busy",void 0),e([pe()],Oi.prototype,"_error",void 0),Oi=e([ue("ir-trigger-dialog")],Oi);const Ui=r`
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
`;let Fi=class extends ne{constructor(){super(...arguments),this.triggers=[],this.receivers=[],this.top=0,this.left=0}render(){return B`
            <div
                class="action-popover"
                style="top:${this.top}px; left:${this.left}px"
            >
                <div class="popover-header">Triggers</div>
                <button
                    class="popover-item accent"
                    @click=${()=>this._emit("create-new")}
                >
                    <span>+ new trigger</span>
                </button>
                <div class="popover-divider"></div>
                ${this.triggers.map(e=>B`
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
        `}_renderScope(e){const t=e.receiver_entity_ids??[];return 0===t.length?"Any receiver":1===t.length?this._friendly(t[0]):`${this._friendly(t[0])} + ${t.length-1} more`}_friendly(e){const t=this.receivers.find(t=>t.entity_id===e);return t?.name??e}_emit(e,t){this.dispatchEvent(new CustomEvent(e,{detail:t,bubbles:!0,composed:!0}))}};Fi.styles=[Ui,r`
            :host {
                display: contents;
            }
        `],e([he({attribute:!1})],Fi.prototype,"triggers",void 0),e([he({attribute:!1})],Fi.prototype,"receivers",void 0),e([he({type:Number})],Fi.prototype,"top",void 0),e([he({type:Number})],Fi.prototype,"left",void 0),Fi=e([ue("ir-trigger-popover")],Fi);const Bi=[{value:"media_player",label:"Media Player"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"light",label:"Light"},{value:"switch",label:"Switch"},{value:"screen",label:"Screen / Shade"},{value:"other",label:"Other"}];let ji=class extends ne{constructor(){super(...arguments),this._busy=!1,this._captureName=null,this._toast=null,this._confirmDelete=!1,this._commandToDelete=null,this._editCommand=null,this._actionOptions=[],this._mappingCommandName=null,this._popoverTop=0,this._popoverLeft=0,this._dismissHandler=null,this._editingName=!1,this._draftName="",this._triggers=[],this._triggerCommand=null,this._triggerEdit=null,this._confirmDeleteTriggerId=null,this._triggerPopover=null,this._receivers=[],this._sortable=null,this._pendingReorderTimeout=null,this._commandsListVersion=0,this._onDocClickForTriggerPopover=e=>{const t=this.shadowRoot?.querySelector("ir-trigger-popover");t&&e.composedPath().includes(t)||this._closeTriggerPopover()},this._onScrollForTriggerPopover=()=>{this._closeTriggerPopover()}}_emitterName(e){const t=this.hass?.states?.[e];return t?.attributes?.friendly_name??e}_deviceRegistryName(e){const t=this.hass?.devices?.[e];return t?.name_by_user??t?.name??e}_deviceConfigEntryId(e){const t=this.hass?.devices?.[e];return t?(t.config_entries??[])[0]??null:null}_configEntryDomain(e){const t=this.hass?.config_entries?.entries?.[e];return t?.domain??null}_integrationUrl(e){if(!e)return null;const t=this._configEntryDomain(e);return t?`/config/integrations/integration/${t}`:null}_entityIntegrationUrl(e){const t=e.split(".")[0],i=this.hass?.entities?.[e];return i?.config_entry_id?this._integrationUrl(i.config_entry_id):i?.platform?`/config/integrations/integration/${i.platform}`:`/config/integrations/integration/${t}`}async _refresh(){this.device=await this.api.getDevice(this.device.id),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}_flash(e){this._toast=e,setTimeout(()=>{this._toast=null},2400)}_startEditName(){this._draftName=this.device.name,this._editingName=!0,this.updateComplete.then(()=>{const e=this.shadowRoot?.querySelector(".name-input");e?.focus(),e?.select()})}async _saveName(){const e=this._draftName.trim();if(e&&e!==this.device.name){this._busy=!0;try{this.device=await this.api.updateDevice(this.device.id,{name:e}),this._flash("Name updated"),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Update failed: ${e.message}`)}finally{this._busy=!1,this._editingName=!1}}else this._editingName=!1}_onNameKeyDown(e){"Enter"===e.key?(e.preventDefault(),this._saveName()):"Escape"===e.key&&(this._editingName=!1)}async _onTypeChanged(e){const t=e.target.value;if(t!==this.device.device_type){this._busy=!0;try{this.device=await this.api.updateDevice(this.device.id,{device_type:t}),this._flash("Device type updated"),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Update failed: ${e.message}`)}finally{this._busy=!1}}}async _onEmittersChanged(e){const t=e.detail.value,i=[...this.device.emitter_entity_ids];this.device={...this.device,emitter_entity_ids:t},this._busy=!0;try{this.device=await this.api.updateDevice(this.device.id,{emitter_entity_ids:t}),this._flash("Emitters updated"),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this.device={...this.device,emitter_entity_ids:i},this._flash(`Update failed: ${e.message}`)}finally{this._busy=!1}}connectedCallback(){super.connectedCallback(),this._loadActionOptions(),this._loadTriggers(),this.api.listReceivers().then(e=>{this._receivers=e}).catch(()=>{this._receivers=[]})}updated(e){e.has("device")&&(this._loadActionOptions(),this._loadTriggers()),e.has("_commandsListVersion")&&!this._sortable&&this._attachSortable()}async _loadActionOptions(){try{this._actionOptions=await this.api.getActionOptions(this.device.device_type)}catch{this._actionOptions=[]}}async _loadTriggers(){try{this._triggers=await this.api.listTriggers()}catch{this._triggers=[]}}_commandHasTrigger(e){return this._triggers.some(t=>t.source_command_id===e.id)}_commandTriggerCount(e){return this._triggers.filter(t=>t.source_command_id===e.id).length}_onToggleTrigger(e){const t=e.detail?.command;if(!t)return;const i=this._triggers.filter(e=>e.source_command_id===t.id);if(0===i.length)return void(this._triggerCommand=t);const s=e.detail?.buttonRect;this._triggerPopover={command:t,top:s?s.bottom+4:120,left:s?Math.max(8,s.right-220):120},this._installTriggerPopoverDismiss()}_triggersForCommand(e){return this._triggers.filter(t=>t.source_command_id===e.id)}_closeTriggerPopover(){this._triggerPopover=null,this._removeTriggerPopoverDismiss()}_onTriggerPopoverCreateNew(){const e=this._triggerPopover;this._closeTriggerPopover(),e&&(this._triggerCommand=e.command)}_onTriggerPopoverEdit(e){const t=e.detail;this._closeTriggerPopover(),t&&(this._triggerEdit=t)}_installTriggerPopoverDismiss(){setTimeout(()=>{document.addEventListener("click",this._onDocClickForTriggerPopover,!0),window.addEventListener("scroll",this._onScrollForTriggerPopover,!0)},0)}_removeTriggerPopoverDismiss(){document.removeEventListener("click",this._onDocClickForTriggerPopover,!0),window.removeEventListener("scroll",this._onScrollForTriggerPopover,!0)}_closeTriggerDialog(){this._triggerCommand=null,this._triggerEdit=null}async _onTriggerSaved(){this._triggerCommand=null,this._triggerEdit=null,await this._loadTriggers(),this.dispatchEvent(new CustomEvent("trigger-changed",{bubbles:!0,composed:!0}))}_requestDeleteTrigger(e){this._confirmDeleteTriggerId=e}async _doDeleteTrigger(){if(!this._confirmDeleteTriggerId)return;const e=this._confirmDeleteTriggerId;this._confirmDeleteTriggerId=null,this._triggerEdit=null;try{await this.api.deleteTrigger(e),await this._loadTriggers(),this.dispatchEvent(new CustomEvent("trigger-changed",{bubbles:!0,composed:!0}))}catch{}}_getActionLabel(e){const t=this.device.entity_config?.command_mapping??{};for(const[i,s]of Object.entries(t))if(s.toLowerCase()===e.toLowerCase()){const e=this._actionOptions.find(e=>e.key===i);return e?.label??i}return null}_onMapAction(e){const{command:t}=e.detail;if(!t)return;const i=e.target.shadowRoot?.querySelector(".badge-btn");if(i){const e=i.getBoundingClientRect();this._popoverTop=e.bottom+4,this._popoverLeft=Math.max(8,e.right-220)}this._mappingCommandName=t.name,requestAnimationFrame(()=>{this._dismissHandler=e=>{const t=e.composedPath(),i=this.shadowRoot?.querySelector(".action-popover");i&&!t.includes(i)&&this._closePopover()},document.addEventListener("click",this._dismissHandler,!0)})}_closePopover(){this._mappingCommandName=null,this._dismissHandler&&(document.removeEventListener("click",this._dismissHandler,!0),this._dismissHandler=null)}disconnectedCallback(){super.disconnectedCallback(),this._dismissHandler&&(document.removeEventListener("click",this._dismissHandler,!0),this._dismissHandler=null),this._removeTriggerPopoverDismiss(),this._sortable?.destroy(),this._sortable=null,this._cancelPendingReorderSave()}firstUpdated(){this._attachSortable()}_attachSortable(){if(this._sortable)return;const e=this.renderRoot.querySelector(".commands-list");e&&(this._sortable=di.create(e,{handle:".grip-handle",animation:150,ghostClass:"sortable-ghost",onEnd:e=>{const t=e.oldIndex,i=e.newIndex;if(void 0===t||void 0===i||t===i)return;const s=[...this.device.commands],[o]=s.splice(t,1);s.splice(i,0,o),this.device={...this.device,commands:s},this.dispatchEvent(new CustomEvent("commands-reordered",{detail:{commands:s},bubbles:!0,composed:!0})),this._sortable?.destroy(),this._sortable=null;const a=this.renderRoot.querySelector(".commands-list");if(a)for(const e of Array.from(a.querySelectorAll("ir-command-row")))e.remove();this._commandsListVersion++,this._scheduleReorderSave(s.map(e=>e.id))}}))}_scheduleReorderSave(e){this._cancelPendingReorderSave(),this._pendingReorderTimeout=window.setTimeout(async()=>{this._pendingReorderTimeout=null;try{await this.api.reorderCommands(this.device.id,e)}catch(e){this._flash(`Reorder failed: ${e.message}`),await this._refresh()}},500)}_cancelPendingReorderSave(){null!==this._pendingReorderTimeout&&(clearTimeout(this._pendingReorderTimeout),this._pendingReorderTimeout=null)}_getCommandForAction(e){return(this.device.entity_config?.command_mapping??{})[e]??null}async _selectAction(e,t){this._closePopover(),this._busy=!0;try{const i=await this.api.updateMapping(this.device.id,e,t);this.device={...this.device,entity_config:{...this.device.entity_config,command_mapping:i.mapping}},this._flash(t?`Mapped to ${t}`:"Mapping cleared"),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Mapping failed: ${e.message}`)}finally{this._busy=!1}}_getCurrentActionKey(e){const t=this.device.entity_config?.command_mapping??{};for(const[i,s]of Object.entries(t))if(s.toLowerCase()===e.toLowerCase())return i;return""}async _onTest(e){const{command:t}=e.detail;if(t){this._busy=!0;try{await this.api.sendCommand(this.device.id,t.id),this._flash(`Sent "${t.name}"`)}catch(e){this._flash(`Send failed: ${e.message}`)}finally{this._busy=!1}}}async _onToggleTxRaw(e){const{command:t}=e.detail;if(!t)return;const i=!t.tx_force_raw;this._busy=!0;try{await this.api.setCommandTxForceRaw(this.device.id,t.id,i),t.tx_force_raw=i,this.requestUpdate(),this._flash(i?`"${t.name}" will transmit the captured timings`:`"${t.name}" will transmit clean decoded timings`)}catch(e){this._flash(`Update failed: ${e.message}`)}finally{this._busy=!1}}_onDelete(e){const{command:t}=e.detail;t&&(this._commandToDelete=t)}_onEditCommand(e){const{command:t}=e.detail;t&&(this._editCommand=t)}async _onCommandEdited(e){const t=e.detail;this._editCommand=null,await this._refresh();const i=t.triggers?.rewired??[];if(i.length){const e=i.map(e=>`"${e}"`).join(", ");this._flash(`Command updated. Re-pointed trigger ${e}.`)}else this._flash("Command updated");this.dispatchEvent(new CustomEvent("trigger-changed",{bubbles:!0,composed:!0}))}async _onRenameCommand(e){const{command:t,name:i}=e.detail;this._busy=!0;try{const e=await this.api.updateCommand({device_id:this.device.id,command_id:t.id,name:i});await this._refresh();const s=e.mappings_updated;this._flash(s>0?`Renamed (updated ${s} action mapping${1===s?"":"s"})`:"Renamed"),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Rename failed: ${e.message}`)}finally{this._busy=!1}}async _confirmCommandDelete(){const e=this._commandToDelete;if(e){this._commandToDelete=null,this._cancelPendingReorderSave(),this._busy=!0;try{await this.api.deleteCommand(this.device.id,e.id),await this._refresh(),this._flash(`Removed "${e.name}"`)}catch(e){this._flash(`Delete failed: ${e.message}`)}finally{this._busy=!1}}}_onCaptureClosed(){this._captureName=null}async _onCommandSaved(e){const{commandName:t}=e.detail;this._cancelPendingReorderSave(),await this._refresh(),this._flash(`Saved "${t}"`),this._captureName=null}_goToSniffer(){this.dispatchEvent(new CustomEvent("navigate-sniffer",{bubbles:!0,composed:!0}))}_goToClips(){this.dispatchEvent(new CustomEvent("navigate-clips",{bubbles:!0,composed:!0}))}async _deleteDevice(){this._busy=!0;try{await this.api.deleteDevice(this.device.id),this.dispatchEvent(new CustomEvent("device-deleted",{bubbles:!0,composed:!0}))}catch(e){this._flash(`Delete failed: ${e.message}`)}finally{this._busy=!1,this._confirmDelete=!1}}_navigateIntegration(e){e&&(window.history.pushState(null,"",e),window.dispatchEvent(new PopStateEvent("popstate")))}render(){const e=this.device.commands,t=e.length;return B`
            <!-- Header: editable name + delete -->
            <section class="header">
                <div class="header-left">
                    ${this._editingName?B`
                              <input
                                  class="name-input"
                                  type="text"
                                  .value=${this._draftName}
                                  @input=${e=>this._draftName=e.target.value}
                                  @blur=${this._saveName}
                                  @keydown=${this._onNameKeyDown}
                                  ?disabled=${this._busy}
                              />
                          `:B`
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
                        ${Bi.map(e=>B`
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
                    ${Se(this._commandsListVersion,e.length>0?Te(e,e=>e.id,e=>B`
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
                                              title="Drag to reorder"
                                          ></ha-svg-icon>
                                      </ir-command-row>
                                  `):B`<div class="empty">No commands yet. Add one below.</div>`)}

                    ${this._mappingCommandName?B`
                              <div
                                  class="action-popover"
                                  style="top:${this._popoverTop}px; left:${this._popoverLeft}px"
                              >
                                  <div class="popover-header">Map action</div>
                                  ${this._getCurrentActionKey(this._mappingCommandName)?B`
                                            <button
                                                class="popover-item clear"
                                                @click=${()=>this._selectAction(this._mappingCommandName,null)}
                                            >
                                                <span class="popover-label">None (clear)</span>
                                            </button>
                                        `:""}
                                  ${this._actionOptions.map(e=>{const t=this._getCurrentActionKey(this._mappingCommandName)===e.key,i=this._getCommandForAction(e.key),s=i&&i.toLowerCase()!==this._mappingCommandName.toLowerCase();return B`
                                          <button
                                              class="popover-item ${t?"active":""}"
                                              @click=${()=>this._selectAction(this._mappingCommandName,e.key)}
                                          >
                                              <span class="popover-label">${e.label}</span>
                                              ${t?B`<span class="popover-check">&#10003;</span>`:s?B`<span class="popover-existing">${i}</span>`:""}
                                          </button>
                                      `})}
                              </div>
                          `:""}
                </div>
            </div>

            <div class="footer-actions">
                <div class="add-group">
                    <button
                        class="action-btn"
                        title="Capture a new signal in the Sniffer"
                        @click=${this._goToSniffer}
                        ?disabled=${this._busy}
                    >+ Sniffed Signal</button>
                    <button
                        class="action-btn"
                        title="Paste a new signal in Clips"
                        @click=${this._goToClips}
                        ?disabled=${this._busy}
                    >+ Clipped Signal</button>
                </div>
                <button
                    class="action-btn delete-btn"
                    @click=${()=>this._confirmDelete=!0}
                    ?disabled=${this._busy}
                >Delete Device</button>
            </div>

            <!-- Dialogs -->
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
            ${this._confirmDelete?B`
                      <ir-confirm-dialog
                          title="Delete ${this.device.name}?"
                          message="This removes all captured commands and the auto-created entity. The action cannot be undone."
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._deleteDevice}
                          @closed=${()=>this._confirmDelete=!1}
                      ></ir-confirm-dialog>
                  `:""}
            ${this._commandToDelete?B`
                      <ir-confirm-dialog
                          title="Delete command?"
                          message="Remove &quot;${this._commandToDelete.name}&quot;? This cannot be undone."
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._confirmCommandDelete}
                          @closed=${()=>this._commandToDelete=null}
                      ></ir-confirm-dialog>
                  `:""}
            ${this._editCommand?B`
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
            ${this._triggerPopover?B`
                      <ir-trigger-popover
                          .triggers=${this._triggersForCommand(this._triggerPopover.command)}
                          .receivers=${this._receivers}
                          .top=${this._triggerPopover.top}
                          .left=${this._triggerPopover.left}
                          @create-new=${this._onTriggerPopoverCreateNew}
                          @edit-trigger=${this._onTriggerPopoverEdit}
                      ></ir-trigger-popover>
                  `:""}
            ${this._triggerCommand?B`
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
            ${this._triggerEdit?B`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .trigger=${this._triggerEdit}
                          @trigger-saved=${this._onTriggerSaved}
                          @closed=${this._closeTriggerDialog}
                          @trigger-delete=${e=>this._requestDeleteTrigger(e.detail.triggerId)}
                      ></ir-trigger-dialog>
                  `:""}
            ${this._confirmDeleteTriggerId?B`
                      <ir-confirm-dialog
                          title="Delete Trigger"
                          message="Remove this trigger? The associated HA event entity will also be removed."
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._doDeleteTrigger}
                          @closed=${()=>this._confirmDeleteTriggerId=null}
                      ></ir-confirm-dialog>
                  `:""}
            ${this._toast?B`<div class="toast" role="status">${this._toast}</div>`:""}
        `}};ji.styles=[Ei,Ui,r`
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
    `],e([he({attribute:!1})],ji.prototype,"api",void 0),e([he({attribute:!1})],ji.prototype,"hass",void 0),e([he({attribute:!1})],ji.prototype,"device",void 0),e([pe()],ji.prototype,"_busy",void 0),e([pe()],ji.prototype,"_captureName",void 0),e([pe()],ji.prototype,"_toast",void 0),e([pe()],ji.prototype,"_confirmDelete",void 0),e([pe()],ji.prototype,"_commandToDelete",void 0),e([pe()],ji.prototype,"_editCommand",void 0),e([pe()],ji.prototype,"_actionOptions",void 0),e([pe()],ji.prototype,"_mappingCommandName",void 0),e([pe()],ji.prototype,"_popoverTop",void 0),e([pe()],ji.prototype,"_popoverLeft",void 0),e([pe()],ji.prototype,"_editingName",void 0),e([pe()],ji.prototype,"_draftName",void 0),e([pe()],ji.prototype,"_triggers",void 0),e([pe()],ji.prototype,"_triggerCommand",void 0),e([pe()],ji.prototype,"_triggerEdit",void 0),e([pe()],ji.prototype,"_confirmDeleteTriggerId",void 0),e([pe()],ji.prototype,"_triggerPopover",void 0),e([pe()],ji.prototype,"_receivers",void 0),e([pe()],ji.prototype,"_commandsListVersion",void 0),ji=e([ue("ir-device-detail")],ji);let qi=class extends ne{constructor(){super(...arguments),this.sourceId="",this.sourceName="",this._name="",this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this._name=`${this.sourceName} (Copy)`}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _duplicate(){const e=this._name.trim();if(e){this._busy=!0,this._error=null;try{const t=await this.api.duplicateDevice(this.sourceId,e);this.dispatchEvent(new CustomEvent("device-duplicated",{detail:t,bubbles:!0,composed:!0})),this._close()}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error="Name is required."}_onKeyDown(e){"Enter"===e.key&&(e.preventDefault(),this._duplicate())}render(){return B`
            <ha-dialog
                open
                heading="Duplicate device"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

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
        `}};qi.styles=r`
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
    `,e([he({attribute:!1})],qi.prototype,"api",void 0),e([he({attribute:!1})],qi.prototype,"sourceId",void 0),e([he({attribute:!1})],qi.prototype,"sourceName",void 0),e([pe()],qi.prototype,"_name",void 0),e([pe()],qi.prototype,"_busy",void 0),e([pe()],qi.prototype,"_error",void 0),qi=e([ue("ir-duplicate-device-dialog")],qi);const Xi={media_player:"M21,17H3V5H21M21,3H3A2,2 0 0,0 1,5V17A2,2 0 0,0 3,19H8V21H16V19H21A2,2 0 0,0 23,17V5A2,2 0 0,0 21,3Z",ac:"M11,21H13V11.85L14.6,13.5L16,12.05L12,8L8,12.05L9.4,13.5L11,11.85V21M2,3V11C2,12.66 5.69,14 12,14C18.31,14 22,12.66 22,11V3H2M4,5H20V8.5C18.5,9.27 15.6,10 12,10C8.4,10 5.5,9.27 4,8.5V5Z",fan:"M12,11A1,1 0 0,0 11,12A1,1 0 0,0 12,13A1,1 0 0,0 13,12A1,1 0 0,0 12,11M12.5,2C17,2 17.11,5.57 14.75,6.75C13.76,7.24 13.32,8.29 13.13,9.22C13.61,9.42 14.03,9.73 14.35,10.13C18.05,8.13 22.03,8.92 22.03,12.5C22.03,17 18.46,17.1 17.28,14.73C16.78,13.74 15.72,13.3 14.79,13.11C14.59,13.59 14.28,14 13.88,14.34C15.87,18.03 15.08,22 11.5,22C7,22 6.91,18.42 9.27,17.24C10.25,16.75 10.69,15.71 10.89,14.79C10.4,14.59 9.97,14.27 9.65,13.87C5.96,15.85 2,15.07 2,11.5C2,7 5.56,6.89 6.74,9.26C7.24,10.25 8.29,10.68 9.22,10.87C9.41,10.39 9.73,9.97 10.14,9.65C8.15,5.95 8.94,2 12.5,2Z",light:"M12,2A7,7 0 0,0 5,9C5,11.38 6.19,13.47 8,14.74V17A1,1 0 0,0 9,18H15A1,1 0 0,0 16,17V14.74C17.81,13.47 19,11.38 19,9A7,7 0 0,0 12,2M9,21A1,1 0 0,0 10,22H14A1,1 0 0,0 15,21V20H9V21Z",switch:"M13,3H11V13H13V3M17.83,5.17L16.41,6.59C18,7.35 19,9.05 19,11A7,7 0 0,1 12,18A7,7 0 0,1 5,11C5,9.05 6,7.35 7.58,6.59L6.17,5.17C4.23,6.82 3,9.26 3,12A9,9 0 0,0 12,21A9,9 0 0,0 21,12C21,9.26 19.77,6.82 17.83,5.17Z",screen:"M20,19H4A2,2 0 0,1 2,17V7A2,2 0 0,1 4,5H20A2,2 0 0,1 22,7V17A2,2 0 0,1 20,19M4,7V17H20V7H4M12,10L16,14H13V17H11V14H8L12,10Z",other:"M11,2A2,2 0 0,0 9,4V8H4A2,2 0 0,0 2,10V13A2,2 0 0,0 4,15H5V21A2,2 0 0,0 7,23H17A2,2 0 0,0 19,21V15H20A2,2 0 0,0 22,13V10A2,2 0 0,0 20,8H15V4A2,2 0 0,0 13,2H11Z"},Zi={media_player:"Media Player",ac:"Air Conditioner",fan:"Fan",light:"Light",switch:"Switch",screen:"Screen / Shade",other:"IR Device"},Yi="M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19M8,9H16V19H8V9M15.5,4L14.5,3H9.5L8.5,4H5V6H19V4H15.5Z";let Wi=class extends ne{constructor(){super(...arguments),this.devices=[],this.loading=!1,this.expandedDeviceId=null,this._emitters=[],this._captureProviders=[],this._pluckBlasters=[],this._expandedDevice=null,this._triggers=[],this._glowTriggerIds=new Set,this._editTrigger=null,this._confirmDeleteTrigger=null,this._duplicateTarget=null,this._confirmDeleteDevice=null,this._devicesVersion=0,this._localDevices=null,this._devicesSortable=null,this._pendingDevicesSave=null,this._unsubTriggerFired=null}connectedCallback(){super.connectedCallback(),this._discoverHardware(),this._loadTriggers(),this._subscribeTriggerFired()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeTriggerFired(),this._devicesSortable?.destroy(),this._devicesSortable=null,null!==this._pendingDevicesSave&&clearTimeout(this._pendingDevicesSave)}willUpdate(e){e.has("devices")&&(this._localDevices=null)}updated(e){(e.has("hass")||e.has("api"))&&this._discoverHardware(),e.has("api")&&this.api&&!this._unsubTriggerFired&&(this._loadTriggers(),this._subscribeTriggerFired()),e.has("expandedDeviceId")&&this._loadExpandedDevice(),this._syncDevicesSortable()}_syncDevicesSortable(){const e=this.renderRoot.querySelector(".device-grid");e&&!this._devicesSortable?this._attachDevicesSortable(e):!e&&this._devicesSortable&&(this._devicesSortable.destroy(),this._devicesSortable=null)}_attachDevicesSortable(e){this._devicesSortable=di.create(e,{draggable:".device-card",filter:".card-action",preventOnFilter:!1,delay:150,delayOnTouchOnly:!0,animation:150,ghostClass:"sortable-ghost",onEnd:()=>{const t=Array.from(e.querySelectorAll(".device-card")).map(e=>e.dataset.id).filter(e=>!!e),i=this._localDevices??this.devices,s=new Map(i.map(e=>[e.id,e])),o=t.map(e=>s.get(e)).filter(e=>!!e);if(o.length===i.length){this._localDevices=o,this._devicesSortable?.destroy(),this._devicesSortable=null;for(const t of Array.from(e.querySelectorAll(".device-card, .expanded-detail")))t.remove();this._devicesVersion++,this._scheduleDevicesSave(o.map(e=>e.id))}}})}_scheduleDevicesSave(e){null!==this._pendingDevicesSave&&clearTimeout(this._pendingDevicesSave),this._pendingDevicesSave=window.setTimeout(async()=>{if(this._pendingDevicesSave=null,this.api)try{await this.api.reorderDevices(e)}catch{this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}},500)}async _loadExpandedDevice(){if(this.expandedDeviceId&&this.api)try{this._expandedDevice=await this.api.getDevice(this.expandedDeviceId)}catch{this._expandedDevice=null}else this._expandedDevice=null}async _onExpandedDeviceChanged(){await this._loadExpandedDevice(),this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}_onExpandedDeviceDeleted(){this.dispatchEvent(new CustomEvent("device-deleted",{bubbles:!0,composed:!0}))}_onCommandsReordered(e){if(!this._expandedDevice)return;const t=e.detail?.commands;Array.isArray(t)&&(this._expandedDevice={...this._expandedDevice,commands:t})}_onCollapse(){this.dispatchEvent(new CustomEvent("device-selected",{detail:this.expandedDeviceId,bubbles:!0,composed:!0}))}async _discoverHardware(){const e=new Set;if(this.api)try{const t=await this.api.listReceivers();for(const i of t)e.add(i.entity_id)}catch{}const t=this.hass?.states??{},i=[];for(const[s,o]of Object.entries(t))!s.startsWith("infrared.")||e.has(s)||o.attributes.hair_observer||i.push({entity_id:s,name:o.attributes.friendly_name??s});if(this._emitters=i,this.api)try{this._captureProviders=await this.api.listCaptureProviders()}catch{}if(this.api)try{const{vendors:e}=await this.api.listPluckVendors(),t=[];for(const i of e)for(const e of i.blasters)t.push({integration:i.integration,entity_id:e.entity_id,name:e.name,vendorName:i.name});this._pluckBlasters=t}catch{this._pluckBlasters=[]}}_select(e){this.dispatchEvent(new CustomEvent("device-selected",{detail:e,bubbles:!0,composed:!0}))}_add(){this.dispatchEvent(new CustomEvent("add-device",{bubbles:!0,composed:!0}))}_openInPlucker(e){this.dispatchEvent(new CustomEvent("navigate-plucker",{detail:{vendor_entity_id:e},bubbles:!0,composed:!0}))}_openDuplicateDialog(e,t){t.stopPropagation(),this._duplicateTarget=e}_closeDuplicateDialog(){this._duplicateTarget=null}_onDeviceDuplicated(){this._duplicateTarget=null,this.dispatchEvent(new CustomEvent("device-changed",{bubbles:!0,composed:!0}))}_requestDeleteDevice(e,t){t.stopPropagation(),this._confirmDeleteDevice=e}async _doDeleteDevice(){if(!this._confirmDeleteDevice||!this.api)return;const e=this._confirmDeleteDevice;this._confirmDeleteDevice=null;try{await this.api.deleteDevice(e.id),this.dispatchEvent(new CustomEvent("device-deleted",{bubbles:!0,composed:!0}))}catch{}}_navigateIntegration(e){const t=`/config/integrations/integration/${e}`;window.history.pushState(null,"",t),window.dispatchEvent(new PopStateEvent("popstate"))}async _loadTriggers(){if(this.api)try{this._triggers=await this.api.listTriggers()}catch{}}async _subscribeTriggerFired(){if(this.api)try{this._unsubTriggerFired=await this.api.subscribeTriggerFired(e=>{this._glowTriggerIds=new Set([...this._glowTriggerIds,e.trigger_id]),setTimeout(()=>{const t=new Set(this._glowTriggerIds);t.delete(e.trigger_id),this._glowTriggerIds=t},2500)})}catch{}}async _unsubscribeTriggerFired(){this._unsubTriggerFired&&(await this._unsubTriggerFired(),this._unsubTriggerFired=null)}_openEditTrigger(e,t){t.stopPropagation(),this._editTrigger=e}_closeEditTrigger(){this._editTrigger=null}async _onTriggerUpdated(){this._editTrigger=null,await this._loadTriggers()}async _toggleTriggerEnabled(e,t){t.stopPropagation();try{await this.api.updateTrigger(e.id,{enabled:!e.enabled}),await this._loadTriggers()}catch{}}_requestDeleteTrigger(e,t){t.stopPropagation(),this._confirmDeleteTrigger=e}async _doDeleteTrigger(){if(!this._confirmDeleteTrigger)return;const e=this._confirmDeleteTrigger;this._confirmDeleteTrigger=null;try{await this.api.deleteTrigger(e.id),await this._loadTriggers()}catch{}}_emitterIntegrationDomain(e){const t=this.hass?.entities?.[e];return t?.platform?t.platform:e.split(".")[0]}_getEmitterDeviceIds(){const e=new Set;for(const t of this._emitters){const i=this.hass?.entities?.[t.entity_id];i?.device_id&&e.add(i.device_id)}return e}_getEmitterEntityIdsByDevice(){const e=new Map;for(const t of this._emitters){const i=this.hass?.entities?.[t.entity_id],s=i?.device_id;if(!s)continue;const o=e.get(s)??[];o.push(t.entity_id),e.set(s,o)}return e}_isPre2026_6(){const e=this.hass?.config?.version;if(!e)return!1;const t=e.match(/^(\d+)\.(\d+)/);if(!t)return!1;const i=parseInt(t[1],10),s=parseInt(t[2],10);return i<2026||2026===i&&s<6}_resolveNavType(e,t){if("native"===e.type&&t){const e=this.hass?.entities?.[t]?.platform;return e||"esphome"}return e.type}_classifyHardware(){const e=this._getEmitterEntityIdsByDevice(),t=new Set(e.keys()),i=new Map;for(const s of this._captureProviders){let o,a;if("native"===s.type?(a=s.receiver_entity_id??s.device_id,o=this.hass?.entities?.[a]?.device_id,o||(o=a)):o=s.device_id,!o)continue;const r=i.get(o)??{device_id:o,name:s.name,nav_type:this._resolveNavType(s,a),has_native:!1,has_bridge:!1,has_tx:t.has(o),tx_entity_ids:e.get(o)??[]};"native"===s.type?(r.has_native=!0,r.native_entity_id=a):(r.has_bridge=!0,r.name=s.name,r.nav_type=s.type),i.set(o,r)}const s=Array.from(i.values()),o=s.filter(e=>e.has_tx);return{receivers:s,proxies:o}}_renderRxBadges(e){const t=!e.has_native&&e.has_bridge&&this._isPre2026_6();return B`
            ${e.has_native?B`<span
                      class="badge rx-native"
                      title="Receives via HA's native infrared platform"
                  >RX-NATIVE</span>`:q}
            ${e.has_bridge?B`<span
                      class="badge rx-bridge"
                      title=${e.has_native?"Legacy bridge still active. Native receiver supersedes it -- you can remove the on_pronto: block from your ESPHome config.":"Receives via legacy ESPHome event-bus bridge"}
                  >RX-BRIDGE</span>`:q}
            ${t?B`<span
                      class="badge rx-native-disabled"
                      title="Upgrade to HA 2026.6+ for native receiver support"
                  >RX-NATIVE</span>`:q}
        `}render(){if(this.loading)return B`<div class="loading">Loading IR devices...</div>`;const e=this._localDevices??this.devices,t=e.length>0,i=this._emitters.length>0,{receivers:s,proxies:o}=this._classifyHardware(),a=s.length>0,r=o.length>0,n=this._triggers.length>0;return t||i||a||r?B`
            <!-- Devices -->
            <div class="toolbar">
                <span class="toolbar-title">
                    <ha-svg-icon .path=${"M17.655 0C17.391 0.034 17.201 0.276 17.235 0.54C17.269 0.804 17.511 0.994 17.775 0.96C17.775 0.96 18.154 0.941 18.81 1.155C19.466 1.369 20.353 1.804 21.255 2.73C22.162 3.66 22.611 4.551 22.83 5.205C23.049 5.859 23.04 6.24 23.04 6.24C23.038 6.412 23.128 6.574 23.278 6.662C23.428 6.748 23.612 6.748 23.762 6.662C23.912 6.574 24.002 6.412 24 6.24C24 6.24 23.991 5.679 23.73 4.905C23.469 4.131 22.957 3.109 21.945 2.07C20.927 1.027 19.894 0.495 19.11 0.24C18.326 -0.015 17.745 0 17.745 0C17.73 0 17.715 0 17.7 0C17.685 0 17.67 0 17.655 0 Z M 13.77 2.88C13.26 2.88 12.746 3.064 12.345 3.435C12.339 3.441 12.336 3.444 12.33 3.45L0.57 15.255C-0.195 16.02 -0.188 17.286 0.555 18.09C0.561 18.096 0.564 18.099 0.57 18.105L5.955 23.475C6.72 24.24 7.971 24.232 8.775 23.49C8.781 23.484 8.784 23.481 8.79 23.475L20.55 11.715C20.556 11.706 20.561 11.694 20.565 11.685C21.289 10.841 21.315 9.6 20.55 8.835L15.165 3.45C14.782 3.067 14.28 2.88 13.77 2.88 Z M 17.67 2.88C17.406 2.904 17.211 3.141 17.235 3.405C17.259 3.669 17.496 3.864 17.76 3.84C17.76 3.84 17.91 3.831 18.21 3.93C18.51 4.029 18.911 4.241 19.335 4.665C19.759 5.089 19.971 5.49 20.07 5.79C20.169 6.09 20.16 6.24 20.16 6.24C20.158 6.412 20.248 6.574 20.398 6.662C20.548 6.748 20.732 6.748 20.882 6.662C21.032 6.574 21.122 6.412 21.12 6.24C21.12 6.24 21.111 5.91 20.97 5.49C20.829 5.07 20.561 4.511 20.025 3.975C19.489 3.439 18.93 3.171 18.51 3.03C18.09 2.889 17.76 2.88 17.76 2.88C17.745 2.88 17.73 2.88 17.715 2.88C17.7 2.88 17.685 2.88 17.67 2.88 Z M 13.77 3.84C14.04 3.84 14.297 3.932 14.49 4.125L19.875 9.51C20.263 9.898 20.274 10.569 19.845 11.07L8.115 22.785C7.671 23.194 7.018 23.188 6.63 22.8L1.26 17.43C1.254 17.424 1.251 17.421 1.245 17.415C0.849 16.971 0.862 16.328 1.245 15.945L13.005 4.14C13.226 3.936 13.5 3.84 13.77 3.84 Z M 13.44 6.72C11.325 6.72 9.6 8.445 9.6 10.56C9.6 12.675 11.325 14.4 13.44 14.4C15.555 14.4 17.28 12.675 17.28 10.56C17.28 8.445 15.555 6.72 13.44 6.72 Z M 13.44 7.68C15.036 7.68 16.32 8.964 16.32 10.56C16.32 12.156 15.036 13.44 13.44 13.44C11.844 13.44 10.56 12.156 10.56 10.56C10.56 8.964 11.844 7.68 13.44 7.68 Z M 13.44 9.6C12.909 9.6 12.48 10.029 12.48 10.56C12.48 11.091 12.909 11.52 13.44 11.52C13.971 11.52 14.4 11.091 14.4 10.56C14.4 10.029 13.971 9.6 13.44 9.6 Z M 7.2 12.96C6.669 12.96 6.24 13.389 6.24 13.92C6.24 14.451 6.669 14.88 7.2 14.88C7.731 14.88 8.16 14.451 8.16 13.92C8.16 13.389 7.731 12.96 7.2 12.96 Z M 4.8 15.36C4.269 15.36 3.84 15.789 3.84 16.32C3.84 16.851 4.269 17.28 4.8 17.28C5.331 17.28 5.76 16.851 5.76 16.32C5.76 15.789 5.331 15.36 4.8 15.36 Z M 10.08 15.84C9.549 15.84 9.12 16.269 9.12 16.8C9.12 17.331 9.549 17.76 10.08 17.76C10.611 17.76 11.04 17.331 11.04 16.8C11.04 16.269 10.611 15.84 10.08 15.84 Z M 7.68 18.24C7.149 18.24 6.72 18.669 6.72 19.2C6.72 19.731 7.149 20.16 7.68 20.16C8.211 20.16 8.64 19.731 8.64 19.2C8.64 18.669 8.211 18.24 7.68 18.24Z"}></ha-svg-icon>
                    HAIR Devices
                    <span class="toolbar-count">(${this.devices.length})</span>
                </span>
                <button class="add-btn" @click=${this._add}>
                    <ha-svg-icon
                        .path=${"M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z"}
                    ></ha-svg-icon>
                    Add Device
                </button>
            </div>
            ${t?B`
                      <div class="grid device-grid">
                          ${Se(this._devicesVersion,Te(e,e=>e.id,e=>B`
                                  <div
                                      class="card device-card ${e.id===this.expandedDeviceId?"expanded":""}"
                                      data-id=${e.id}
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
                                          <ha-svg-icon .path=${Yi}></ha-svg-icon>
                                      </button>
                                      <div class="card-header">
                                          <ha-svg-icon
                                              .path=${Xi[e.device_type]??Xi.other}
                                          ></ha-svg-icon>
                                          <div class="card-name">
                                              ${e.name}
                                          </div>
                                      </div>
                                      <div class="card-meta">
                                          ${[e.manufacturer,Zi[e.device_type]].filter(Boolean).join(" • ")}
                                      </div>
                                      <div class="card-footer">
                                          <span class="badge cmd-badge">
                                              CMD: ${e.command_count}
                                          </span>
                                          ${e.emitter_entity_ids.length>0?B`<span class="badge tx-badge">TX: ${e.emitter_entity_ids.length}</span>`:B`<span class="badge no-tx-badge">No TX</span>`}
                                      </div>
                                  </div>
                                  ${e.id===this.expandedDeviceId&&this._expandedDevice?B`
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
                                        `:q}
                              `))}
                      </div>
                  `:B`
                      <div class="empty-devices">
                          No devices yet. Sniff some signals, then add your first device.
                      </div>
                  `}

            <!-- Triggers -->
            ${n?B`
                      <div class="section-header">
                          <h2>Triggers</h2>
                          <span class="section-count">${this._triggers.length}</span>
                      </div>
                      <div class="grid">
                          ${this._triggers.map(e=>B`
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
                                          ${e.min_hits>1?B`<span class="badge trigger-hits-badge">
                                                    ${e.min_hits}x hits
                                                </span>`:q}
                                          <span
                                              class="badge trigger-toggle ${e.enabled?"trigger-enabled":"trigger-off"}"
                                              @click=${t=>this._toggleTriggerEnabled(e,t)}
                                          >${e.enabled?"ON":"OFF"}</span>
                                          <ha-svg-icon
                                              class="trigger-trash"
                                              .path=${Yi}
                                              title="Delete trigger"
                                              @click=${t=>this._requestDeleteTrigger(e,t)}
                                          ></ha-svg-icon>
                                      </div>
                                  </div>
                              `)}
                      </div>
                  `:q}

            <!-- Blasters (Pluckable) -- vendor IR blasters HAIR can pull from -->
            ${this._pluckBlasters.length>0?B`
                      <div class="section-header">
                          <h2>Blasters (Pluckable)</h2>
                          <span class="section-count"
                              >${this._pluckBlasters.length}</span
                          >
                      </div>
                      <div class="grid">
                          ${this._pluckBlasters.map(e=>B`
                                  <div
                                      class="card hw-card"
                                      tabindex="0"
                                      title="Open in the Plucker"
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
                                              >Open in Plucker</span
                                          >
                                      </div>
                                  </div>
                              `)}
                      </div>
                  `:q}

            <!-- Emitters -->
            ${i?B`
                      <div class="section-header">
                          <h2>Emitters</h2>
                          <span class="section-count">${this._emitters.length}</span>
                      </div>
                      <div class="grid">
                          ${this._emitters.map(e=>B`
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
                  `:q}

            <!-- Receivers (capture-capable hardware; proxies appear here too by design) -->
            ${a?B`
                      <div class="section-header">
                          <h2>Receivers</h2>
                          <span class="section-count">${s.length}</span>
                      </div>
                      <div class="grid">
                          ${s.map(e=>B`
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
                  `:q}

            <!-- Proxies (TX + RX hardware) -->
            ${r?B`
                      <div class="section-header">
                          <h2>Proxies</h2>
                          <span class="section-count">${o.length}</span>
                      </div>
                      <div class="grid">
                          ${o.map(e=>B`
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
                                      ${e.tx_entity_ids[0]?B`<div class="card-meta">${e.tx_entity_ids[0]}</div>`:q}
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
                  `:q}

            ${this._editTrigger?B`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .trigger=${this._editTrigger}
                          @trigger-saved=${this._onTriggerUpdated}
                          @closed=${this._closeEditTrigger}
                      ></ir-trigger-dialog>
                  `:q}

            ${this._confirmDeleteTrigger?B`
                      <ir-confirm-dialog
                          title="Delete Trigger"
                          message="Remove &quot;${this._confirmDeleteTrigger.name}&quot;? The associated HA event entity will also be removed."
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._doDeleteTrigger}
                          @closed=${()=>this._confirmDeleteTrigger=null}
                      ></ir-confirm-dialog>
                  `:q}

            ${this._duplicateTarget&&this.api?B`
                      <ir-duplicate-device-dialog
                          .api=${this.api}
                          .sourceId=${this._duplicateTarget.id}
                          .sourceName=${this._duplicateTarget.name}
                          @device-duplicated=${this._onDeviceDuplicated}
                          @closed=${this._closeDuplicateDialog}
                      ></ir-duplicate-device-dialog>
                  `:q}

            ${this._confirmDeleteDevice?B`
                      <ir-confirm-dialog
                          title="Delete Device"
                          message="Remove &quot;${this._confirmDeleteDevice.name}&quot;? Commands, action mappings, and emitter assignments will be deleted. Triggers are unaffected."
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._doDeleteDevice}
                          @closed=${()=>this._confirmDeleteDevice=null}
                      ></ir-confirm-dialog>
                  `:q}
        `:B`
                <ha-card class="empty">
                    <h2>No IR devices yet</h2>
                    <p>Add your first device to get started.</p>
                    <mwc-button raised @click=${this._add}>+ Add Device</mwc-button>
                </ha-card>
            `}};Wi.styles=r`
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
    `,e([he({attribute:!1})],Wi.prototype,"devices",void 0),e([he({attribute:!1})],Wi.prototype,"hass",void 0),e([he({attribute:!1})],Wi.prototype,"api",void 0),e([he({type:Boolean})],Wi.prototype,"loading",void 0),e([he({attribute:!1})],Wi.prototype,"expandedDeviceId",void 0),e([pe()],Wi.prototype,"_emitters",void 0),e([pe()],Wi.prototype,"_captureProviders",void 0),e([pe()],Wi.prototype,"_pluckBlasters",void 0),e([pe()],Wi.prototype,"_expandedDevice",void 0),e([pe()],Wi.prototype,"_triggers",void 0),e([pe()],Wi.prototype,"_glowTriggerIds",void 0),e([pe()],Wi.prototype,"_editTrigger",void 0),e([pe()],Wi.prototype,"_confirmDeleteTrigger",void 0),e([pe()],Wi.prototype,"_duplicateTarget",void 0),e([pe()],Wi.prototype,"_confirmDeleteDevice",void 0),e([pe()],Wi.prototype,"_devicesVersion",void 0),e([pe()],Wi.prototype,"_localDevices",void 0),Wi=e([ue("ir-device-list")],Wi);const Ki=[{value:"media_player",label:"Media Player"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"light",label:"Light"},{value:"switch",label:"Switch"},{value:"screen",label:"Screen / Shade"},{value:"other",label:"Other"}];let Gi=class extends ne{constructor(){super(...arguments),this._name="",this._deviceType="media_player",this._emitterIds=[],this._captureProviders=[],this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this._loadCaptureProviders()}async _loadCaptureProviders(){try{this._captureProviders=await this.api.listCaptureProviders()}catch{}}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _create(){if(this._name.trim())if(0!==this._emitterIds.length){this._busy=!0,this._error=null;try{const e=this._captureProviders[0]??null,t=await this.api.createDevice({name:this._name.trim(),device_type:this._deviceType,emitter_entity_ids:this._emitterIds,capture_device_id:e?.device_id??null,capture_provider_type:e?.type??"esphome"});this.dispatchEvent(new CustomEvent("device-created",{detail:t,bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error="Pick at least one IR emitter.";else this._error="Name is required."}render(){return B`
            <ha-dialog
                open
                heading="Add Device"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

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
                        ${Ki.map(e=>B`
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
        `}};Gi.styles=r`
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
    `,e([he({attribute:!1})],Gi.prototype,"api",void 0),e([he({attribute:!1})],Gi.prototype,"hass",void 0),e([pe()],Gi.prototype,"_name",void 0),e([pe()],Gi.prototype,"_deviceType",void 0),e([pe()],Gi.prototype,"_emitterIds",void 0),e([pe()],Gi.prototype,"_captureProviders",void 0),e([pe()],Gi.prototype,"_busy",void 0),e([pe()],Gi.prototype,"_error",void 0),Gi=e([ue("ir-add-device-dialog")],Gi);let Ji=class extends ne{constructor(){super(...arguments),this.deviceId="",this.disabled=!1,this._editing=!1,this._draft=""}updated(e){if(e.has("_editing")&&this._editing){const e=this.shadowRoot?.querySelector(".alias-input");e?.focus(),e?.select()}}_startEdit(e){this.disabled||(e?.stopPropagation(),this._draft=this.signal.alias??"",this._editing=!0)}_onKeydown(e){"Enter"===e.key?this._commit():"Escape"===e.key&&(this._editing=!1)}async _commit(){if(!this._editing)return;const e=this._draft.trim();this._editing=!1,await this._save(e)}async _clear(){this._editing=!1,await this._save("")}async _save(e){try{await this.api.setSignalAlias(this.deviceId,this.signal.id,e),this.dispatchEvent(new CustomEvent("alias-changed",{detail:{id:this.signal.id,alias:e},bubbles:!0,composed:!0}))}catch(e){this.dispatchEvent(new CustomEvent("alias-error",{detail:e.message,bubbles:!0,composed:!0}))}}render(){const e=this.signal;return this._editing?B`
                <span class="alias-edit" @click=${e=>e.stopPropagation()}>
                    <input
                        class="alias-input"
                        type="text"
                        .value=${this._draft}
                        placeholder="Alias for this signal"
                        @input=${e=>{this._draft=e.target.value}}
                        @keydown=${this._onKeydown}
                        @blur=${()=>{this._commit()}}
                    />
                    <button
                        class="alias-clear"
                        title="Clear alias"
                        @mousedown=${e=>e.preventDefault()}
                        @click=${()=>{this._clear()}}
                    >✕</button>
                </span>
            `:e.alias?B`
                <span
                    class="alias-display ${this.disabled?"locked":""}"
                    title=${this.disabled?"":"Click to edit alias"}
                    @click=${e=>this._startEdit(e)}
                >
                    <span class="alias-label">alias</span>
                    <span class="alias-name">${e.alias}</span>
                </span>
            `:B`
            <span
                class="diamonds-wrap ${this.disabled?"locked":""}"
                title=${this.disabled?"":"Click to name this signal"}
                @click=${e=>this._startEdit(e)}
            >
                ${e.sl_pattern?B`<span class="diamonds"
                          >${[...e.sl_pattern].map(e=>"L"===e?B`<span class="diamond long">◆</span>`:B`<span class="diamond short">◇</span>`)}</span
                      >`:B`<span class="signal-short-label">IR Signal</span>`}
                <ha-svg-icon class="alias-pencil" .path=${"M14.06,9L15,9.94L5.92,19H5V18.08L14.06,9M17.66,3C17.41,3 17.15,3.1 16.96,3.29L15.13,5.12L18.88,8.87L20.71,7.04C21.1,6.65 21.1,6.02 20.71,5.63L18.37,3.29C18.17,3.09 17.92,3 17.66,3M14.06,6.19L3,17.25V21H6.75L17.81,9.94L14.06,6.19Z"}></ha-svg-icon>
            </span>
        `}};Ji.styles=r`
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
    `,e([he({attribute:!1})],Ji.prototype,"api",void 0),e([he()],Ji.prototype,"deviceId",void 0),e([he({attribute:!1})],Ji.prototype,"signal",void 0),e([he({type:Boolean})],Ji.prototype,"disabled",void 0),e([pe()],Ji.prototype,"_editing",void 0),e([pe()],Ji.prototype,"_draft",void 0),Ji=e([ue("ir-signal-alias")],Ji);const Qi=[{value:"media_player",label:"Media Player"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"light",label:"Light"},{value:"switch",label:"Switch"},{value:"screen",label:"Screen / Shade"},{value:"other",label:"Other"}];let es=class extends ne{constructor(){super(...arguments),this.suggestedDeviceName="",this.initialMode="existing",this._mode="existing",this._devices=[],this._selectedDeviceId="",this._commandName="",this._newName="",this._newType="media_player",this._newEmitterIds=[],this._templates=[],this._customCommand=!1,this._sendCount=1,this._dittoCount=1,this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this._mode=this.initialMode,this.suggestedDeviceName&&!this._newName&&(this._newName=this.suggestedDeviceName),this._dittoCount=this.signal?.repeat_count??1,this._loadDevices(),"new"===this._mode&&this._loadTemplates(this._newType)}async _loadDevices(){try{if(this._devices=await this.api.listDevices(),this.suggestedDeviceName&&!this._selectedDeviceId){const e=this.suggestedDeviceName.toLowerCase(),t=this._devices.find(t=>t.name.toLowerCase()===e);if(t)return this._selectedDeviceId=t.id,void this._loadTemplates(t.device_type)}if("existing"===this._mode&&this._devices.length>0){const e=this._devices[0];this._loadTemplates(e.device_type)}else"existing"===this._mode&&this._loadTemplates("other")}catch{"existing"===this._mode&&this._loadTemplates("other")}}async _loadTemplates(e){try{this._templates=await this.api.listTemplates(e)}catch{this._templates=[]}this._customCommand||(this._commandName="")}_activeDeviceType(){if("new"===this._mode)return this._newType;const e=this._devices.find(e=>e.id===this._selectedDeviceId);return e?.device_type??"other"}_onDeviceSelected(e){this._selectedDeviceId=e.target.value;const t=this._devices.find(e=>e.id===this._selectedDeviceId);t&&this._loadTemplates(t.device_type)}_onNewTypeChanged(e){this._newType=e.target.value,this._loadTemplates(this._newType)}_switchMode(e){e!==this._mode&&(this._mode=e,this._customCommand=!1,this._commandName="",this._loadTemplates(this._activeDeviceType()))}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_onSendCountInput(e){const t=parseInt(e.target.value,10);this._sendCount=Number.isNaN(t)?1:Math.max(1,Math.min(t,10))}_onDittoInput(e){const t=parseInt(e.target.value,10);this._dittoCount=Number.isNaN(t)?0:Math.max(0,Math.min(t,20))}async _assign(){const e=this._commandName.trim();if(e){this._busy=!0,this._error=null;try{let t;if("existing"===this._mode){if(!this._selectedDeviceId)return this._error="Select a target device.",void(this._busy=!1);t=await this.api.assignSignal({device_id:this.unknownDeviceId,signal_id:this.signal.id,hair_device_id:this._selectedDeviceId,command_name:e,send_count:this._sendCount,repeat_count:this.signal.decoded_fingerprint?this._dittoCount:void 0})}else{if(!this._newName.trim())return this._error="Device name is required.",void(this._busy=!1);if(0===this._newEmitterIds.length)return this._error="Select at least one IR emitter.",void(this._busy=!1);t=await this.api.assignToNewDevice({device_id:this.unknownDeviceId,signal_id:this.signal.id,device_name:this._newName.trim(),device_type:this._newType,emitter_entity_ids:this._newEmitterIds,command_name:e,send_count:this._sendCount,repeat_count:this.signal.decoded_fingerprint?this._dittoCount:void 0})}t.assigned?this.dispatchEvent(new CustomEvent("signal-assigned",{detail:t,bubbles:!0,composed:!0})):this._error="Assignment failed. The signal may have a duplicate code on the target device."}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error="Command name is required."}_fmtTime(e){try{return new Date(e).toLocaleString(void 0,{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return e}}render(){const e=this.signal.frequency?`${Math.round(this.signal.frequency/1e3)}kHz`:"";return B`
            <ha-dialog
                open
                heading="Assign Signal"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <div class="signal-header">
                    ${this.suggestedDeviceName?B`<div class="device-name">${this.suggestedDeviceName}</div>`:""}
                    <div class="signal-detail">
                        <ir-signal-alias
                            .api=${this.api}
                            .deviceId=${this.unknownDeviceId}
                            .signal=${this.signal}
                            disabled
                        ></ir-signal-alias>
                    </div>
                    <div class="signal-stats">
                        <span>${this.signal.hit_count} hits</span>
                        ${e?B`<span>${e}</span>`:""}
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

                <!-- Whole-frame send count (shared by both modes) -->
                <div class="field">
                    <label>Send times</label>
                    <input
                        class="send-count"
                        type="number"
                        min="1"
                        max="10"
                        .value=${String(this._sendCount)}
                        @input=${this._onSendCountInput}
                    />
                    <div class="hint">
                        Transmit this command this many times per press, for
                        devices that need a repeat. Default 1.
                    </div>
                </div>

                ${this.signal.decoded_fingerprint?B`<!-- NEC ditto count (decoded signals only) -->
                          <div class="field">
                              <label>Ditto count</label>
                              <input
                                  class="send-count"
                                  type="number"
                                  min="0"
                                  max="20"
                                  .value=${String(this._dittoCount)}
                                  title="Append repeat frames after the main frame; some strict receivers need at least one to register the command."
                                  @input=${this._onDittoInput}
                              />
                              <div class="hint">
                                  Append repeat frames after the main frame;
                                  some strict receivers require at least one
                                  to register the command.
                              </div>
                          </div>`:""}

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
        `}_renderExistingMode(){return B`
            <div class="field">
                <label>Target device</label>
                ${0===this._devices.length?B`<ha-alert alert-type="info">
                          No devices yet. Switch to "New Device" to create one.
                      </ha-alert>`:B`
                          <select
                              .value=${this._selectedDeviceId}
                              @change=${this._onDeviceSelected}
                          >
                              <option value="" disabled>Select device...</option>
                              ${this._devices.map(e=>B`
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
        `}_renderNewMode(){return B`
            <div class="field">
                <label>Device name</label>
                <input
                    type="text"
                    .value=${this._newName}
                    placeholder="e.g. Living Room TV"
                    required
                    autofocus
                    @input=${e=>this._newName=e.target.value}
                />
            </div>

            <div class="field">
                <label>Device type</label>
                <select
                    .value=${this._newType}
                    @change=${this._onNewTypeChanged}
                >
                    ${Qi.map(e=>B`
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
        `}_onCommandSelect(e){const t=e.target.value;"__custom__"===t?(this._customCommand=!0,this._commandName="",this.updateComplete.then(()=>{const e=this.shadowRoot?.querySelector(".custom-cmd-input");e?.focus()})):(this._customCommand=!1,this._commandName=t)}_renderCommandPicker(){return this._customCommand?B`
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
            `:B`
            <div class="field">
                <label>Command name</label>
                <select
                    .value=${this._commandName}
                    @change=${this._onCommandSelect}
                >
                    <option value="" disabled ?selected=${!this._commandName}>
                        Select command...
                    </option>
                    ${this._templates.map(e=>B`
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
        `}};es.styles=r`
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
    `,e([he({attribute:!1})],es.prototype,"api",void 0),e([he({attribute:!1})],es.prototype,"hass",void 0),e([he()],es.prototype,"unknownDeviceId",void 0),e([he({attribute:!1})],es.prototype,"signal",void 0),e([he()],es.prototype,"suggestedDeviceName",void 0),e([he()],es.prototype,"initialMode",void 0),e([pe()],es.prototype,"_mode",void 0),e([pe()],es.prototype,"_devices",void 0),e([pe()],es.prototype,"_selectedDeviceId",void 0),e([pe()],es.prototype,"_commandName",void 0),e([pe()],es.prototype,"_newName",void 0),e([pe()],es.prototype,"_newType",void 0),e([pe()],es.prototype,"_newEmitterIds",void 0),e([pe()],es.prototype,"_templates",void 0),e([pe()],es.prototype,"_customCommand",void 0),e([pe()],es.prototype,"_sendCount",void 0),e([pe()],es.prototype,"_dittoCount",void 0),e([pe()],es.prototype,"_busy",void 0),e([pe()],es.prototype,"_error",void 0),es=e([ue("ir-assign-signal-dialog")],es);const ts=[{value:"media_player",label:"Media Player"},{value:"ac",label:"Air Conditioner"},{value:"fan",label:"Fan"},{value:"light",label:"Light"},{value:"switch",label:"Switch"},{value:"screen",label:"Screen / Shade"},{value:"other",label:"Other"}];let is=class extends ne{constructor(){super(...arguments),this.suggestedName="",this._name="",this._type="other",this._emitterIds=[],this._busy=!1,this._error=null}connectedCallback(){super.connectedCallback(),this.suggestedName&&!this._name&&(this._name=this.suggestedName)}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _create(){const e=this._name.trim();if(e)if(0!==this._emitterIds.length){this._busy=!0,this._error=null;try{await this.api.createDevice({name:e,device_type:this._type,emitter_entity_ids:this._emitterIds}),this.dispatchEvent(new CustomEvent("device-created",{bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error="Select at least one IR emitter.";else this._error="Device name is required."}render(){return B`
            <ha-dialog
                open
                heading="Promote to Device"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

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
                        ${ts.map(e=>B`
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
        `}};is.styles=r`
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
    `,e([he({attribute:!1})],is.prototype,"api",void 0),e([he({attribute:!1})],is.prototype,"hass",void 0),e([he()],is.prototype,"suggestedName",void 0),e([pe()],is.prototype,"_name",void 0),e([pe()],is.prototype,"_type",void 0),e([pe()],is.prototype,"_emitterIds",void 0),e([pe()],is.prototype,"_busy",void 0),e([pe()],is.prototype,"_error",void 0),is=e([ue("ir-promote-dialog")],is);let ss=class extends ne{constructor(){super(...arguments),this.value=[],this.busy=!1,this._local=[]}connectedCallback(){super.connectedCallback(),this._local=[...this.value]}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}_send(){0!==this._local.length&&this.dispatchEvent(new CustomEvent("send",{detail:{emitters:[...this._local]},bubbles:!0,composed:!0}))}_onEmittersChanged(e){this._local=e.detail.value,this.dispatchEvent(new CustomEvent("emitters-changed",{detail:{value:this._local},bubbles:!0,composed:!0}))}render(){const e=this._local.length>0&&!this.busy;return B`
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
        `}};ss.styles=r`
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
    `,e([he({attribute:!1})],ss.prototype,"api",void 0),e([he({attribute:!1})],ss.prototype,"hass",void 0),e([he({attribute:!1})],ss.prototype,"value",void 0),e([he({type:Boolean})],ss.prototype,"busy",void 0),e([pe()],ss.prototype,"_local",void 0),ss=e([ue("ir-test-emitter-dialog")],ss);let os=class extends ne{constructor(){super(...arguments),this.assignments=[],this.top=0,this.left=0}render(){return B`
            <div
                class="action-popover"
                style="top:${this.top}px; left:${this.left}px"
            >
                <div class="popover-header">Assigned to</div>
                <button
                    class="popover-item accent"
                    @click=${()=>this._emit("create-new")}
                >
                    <span>+ new assignment</span>
                </button>
                <div class="popover-divider"></div>
                ${this.assignments.map(e=>B`
                        <button
                            class="popover-item"
                            title="Open ${e.device_name} in Devices"
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
        `}_emit(e,t){this.dispatchEvent(new CustomEvent(e,{detail:t,bubbles:!0,composed:!0}))}};os.styles=[Ui,r`
            :host {
                display: contents;
            }
            .chevron {
                --mdc-icon-size: 14px;
                color: var(--secondary-text-color);
                flex: none;
            }
        `],e([he({attribute:!1})],os.prototype,"assignments",void 0),e([he({type:Number})],os.prototype,"top",void 0),e([he({type:Number})],os.prototype,"left",void 0),os=e([ue("ir-assigned-popover")],os);const as="hair-mirror";function rs(e,t){const i=e.decoded_fingerprint??null,s=t.decoded_fingerprint??null;if(null!==i&&null!==s)return i===s;const o=e.byte_hash??null,a=t.byte_hash??null;return null!==o&&null!==a?o===a:e.signal_fingerprint===t.fingerprint}var ns;function ls(e){try{return new Date(e).toLocaleString(void 0,{month:"short",day:"numeric",hour:"2-digit",minute:"2-digit"})}catch{return e}}function ds(e){try{const t=Date.now()-new Date(e).getTime();return t<6e4?"just now":t<36e5?`${Math.floor(t/6e4)} min ago`:t<864e5?`${Math.floor(t/36e5)}h ago`:`${Math.floor(t/864e5)}d ago`}catch{return""}}const cs="M12 9.188c-1.553 0-2.812 1.259-2.812 2.812s1.259 2.812 2.812 2.812c1.553 0 2.812-1.259 2.812-2.812v0c-0.002-1.552-1.26-2.81-2.812-2.812h-0zM12 13.688c-0.932 0-1.688-0.755-1.688-1.688s0.755-1.688 1.688-1.688c0.932 0 1.688 0.755 1.688 1.688v0c-0.002 0.931-0.756 1.686-1.688 1.688h-0zM2.062 12c0.16-2.665 1.25-5.049 2.948-6.856l-0.005 0.006c0.098-0.101 0.159-0.239 0.159-0.392 0-0.31-0.252-0.562-0.562-0.562-0.153 0-0.291 0.061-0.393 0.16l0-0c-1.906 1.998-3.125 4.667-3.27 7.618l-0.001 0.028c0.146 2.979 1.365 5.647 3.275 7.652l-0.005-0.005c0.101 0.098 0.239 0.159 0.392 0.159 0.31 0 0.562-0.252 0.562-0.562 0-0.152-0.061-0.291-0.16-0.392l0 0c-1.694-1.8-2.785-4.185-2.94-6.821l-0.002-0.03zM6.647 12c0.113-1.859 0.874-3.523 2.058-4.784l-0.004 0.004c0.098-0.101 0.159-0.239 0.159-0.392 0-0.31-0.252-0.562-0.562-0.562-0.153 0-0.291 0.061-0.392 0.16l0-0c-1.39 1.457-2.278 3.403-2.383 5.554l-0.001 0.02c0.105 2.171 0.994 4.117 2.386 5.577l-0.003-0.004c0.102 0.104 0.244 0.167 0.4 0.167 0.31 0 0.562-0.251 0.562-0.562 0-0.156-0.064-0.297-0.167-0.399l-0-0c-1.183-1.256-1.944-2.92-2.053-4.759l-0.001-0.021zM19.793 4.355c-0.102-0.101-0.241-0.164-0.396-0.164-0.31 0-0.562 0.252-0.562 0.562 0 0.154 0.062 0.294 0.162 0.395l-0-0c1.691 1.802 2.782 4.185 2.94 6.82l0.002 0.03c-0.16 2.665-1.249 5.05-2.947 6.857l0.005-0.006c-0.105 0.102-0.17 0.244-0.17 0.403 0 0.31 0.252 0.562 0.562 0.562 0.158 0 0.301-0.065 0.404-0.171l0-0c1.906-1.999 3.125-4.667 3.268-7.618l0.001-0.028c-0.146-2.978-1.364-5.647-3.274-7.65l0.005 0.005zM15.299 6.425c-0.102 0.102-0.165 0.242-0.165 0.398 0 0.154 0.062 0.295 0.164 0.397l-0-0c1.181 1.257 1.942 2.92 2.054 4.758l0.001 0.022c-0.114 1.86-0.875 3.523-2.059 4.784l0.004-0.004c-0.101 0.102-0.164 0.241-0.164 0.396 0 0.311 0.252 0.563 0.563 0.563 0.155 0 0.295-0.062 0.397-0.164l-0 0c1.389-1.458 2.277-3.404 2.383-5.555l0.001-0.02c-0.105-2.172-0.994-4.118-2.388-5.578l0.003 0.003c-0.101-0.102-0.242-0.165-0.397-0.165s-0.295 0.063-0.397 0.165l-0 0z",hs="M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z";let ps=ns=class extends ne{constructor(){super(...arguments),this._devices=[],this._hairDevices=[],this._loading=!0,this._error=null,this._hasReceivers=!0,this._showDismissed=!1,this._expandedId=null,this._expandedDevice=null,this._flashIds=new Set,this._flashStats=new Set,this._recentSignalIds=[],this._glowSignalIds=new Set,this._hitFlashSignalIds=new Set,this._confirmClearAll=!1,this._triggers=[],this._triggerDialog=null,this._triggerEditDialog=null,this._confirmDeleteTriggerId=null,this._triggerPopover=null,this._assignedPopover=null,this._receivers=[],this._unsubUpdated=null,this._editingDeviceId=null,this._editLabel="",this._promoteTarget=null,this._assignSignal=null,this._deleteSignal=null,this._editSignal=null,this._testingSignalId=null,this._testResult=null,this._testDialog=null,this._testEmitters=[],this._dismissGlowActive=!1,this._dismissDotVisible=!1,this._unsubLive=null,this._unsubRemoved=null,this._unsubDismiss=null,this._dismissGlowTimer=null,this._remotesVersion=0,this._signalsVersion=0,this._remotesSortable=null,this._signalsSortable=null,this._signalsSortableContainer=null,this._pendingRemotesSave=null,this._pendingSignalsSave=null,this._onDocClickForPopover=e=>{const t=e.composedPath(),i=this.shadowRoot?.querySelector("ir-trigger-popover"),s=this.shadowRoot?.querySelector("ir-assigned-popover");i&&t.includes(i)||s&&t.includes(s)||(this._closeTriggerPopover(),this._closeAssignedPopover())},this._onScrollForPopover=()=>{this._closeTriggerPopover(),this._closeAssignedPopover()}}connectedCallback(){super.connectedCallback(),this._load(),this._subscribeLive(),this._subscribeRemoved(),this._subscribeDismissActivity(),this._subscribeUpdated()}updated(e){if(super.updated(e),e.has("_editingDeviceId")&&this._editingDeviceId){const e=this.shadowRoot?.querySelector(".rename-input");e&&(e.focus(),e.select())}this._syncSortables()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeLive(),this._unsubscribeRemoved(),this._unsubscribeDismissActivity(),this._unsubscribeUpdated(),this._removePopoverDismiss(),null!==this._dismissGlowTimer&&(clearTimeout(this._dismissGlowTimer),this._dismissGlowTimer=null),this._remotesSortable?.destroy(),this._remotesSortable=null,this._signalsSortable?.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null,null!==this._pendingRemotesSave&&clearTimeout(this._pendingRemotesSave),null!==this._pendingSignalsSave&&clearTimeout(this._pendingSignalsSave)}_syncSortables(){const e=this.renderRoot.querySelector(".device-list");e&&!this._remotesSortable?this._attachRemotesSortable(e):!e&&this._remotesSortable&&(this._remotesSortable.destroy(),this._remotesSortable=null);const t=this.renderRoot.querySelector(".signal-list"),i=!!this._expandedDevice&&!this._expandedDevice.dismissed;!t||!i||this._signalsSortable&&this._signalsSortableContainer===t?t&&i||!this._signalsSortable||(this._signalsSortable.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null):(this._signalsSortable?.destroy(),this._attachSignalsSortable(t))}_attachRemotesSortable(e){this._remotesSortable=di.create(e,{handle:".remote-grip",animation:150,ghostClass:"sortable-ghost",onEnd:t=>{const{oldIndex:i,newIndex:s}=t;if(void 0===i||void 0===s||i===s)return;const o=[...this._devices],[a]=o.splice(i,1);o.splice(s,0,a),this._devices=o,this._remotesSortable?.destroy(),this._remotesSortable=null,this._purgeChildren(e,"ha-card"),this._remotesVersion++,this._scheduleRemotesSave(o.map(e=>e.id))}})}_attachSignalsSortable(e){this._expandedDevice&&(this._signalsSortableContainer=e,this._signalsSortable=di.create(e,{handle:".signal-grip",animation:150,ghostClass:"sortable-ghost",onEnd:t=>{const{oldIndex:i,newIndex:s}=t;if(void 0===i||void 0===s||i===s)return;const o=this._expandedDevice;if(!o)return;const a=[...o.signals],[r]=a.splice(i,1);a.splice(s,0,r),this._expandedDevice={...o,signals:a},this._signalsSortable?.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null,this._purgeChildren(e,".signal-row"),this._signalsVersion++,this._scheduleSignalsSave(o.id,a.map(e=>e.id))}}))}_purgeChildren(e,t){for(const i of Array.from(e.querySelectorAll(t)))i.remove()}_scheduleRemotesSave(e){null!==this._pendingRemotesSave&&clearTimeout(this._pendingRemotesSave),this._pendingRemotesSave=window.setTimeout(async()=>{this._pendingRemotesSave=null;try{await this.api.reorderUnknownDevices("sniffed",e)}catch(e){this._error=`Reorder failed: ${e.message}`,await this._load()}},500)}_scheduleSignalsSave(e,t){null!==this._pendingSignalsSave&&clearTimeout(this._pendingSignalsSave),this._pendingSignalsSave=window.setTimeout(async()=>{this._pendingSignalsSave=null;try{await this.api.reorderUnknownSignals(e,t)}catch(e){this._error=`Reorder failed: ${e.message}`}},500)}async _load(){this._loading=!0;try{const[e,t,i,s]=await Promise.all([this.api.getUnknownDevices({include_dismissed:this._showDismissed,source:"sniffed"}),this.api.listDevices(),this.api.listTriggers(),this.api.getSnifferStatus()]);this._devices=e,this._hairDevices=t,this._triggers=i,this._hasReceivers=s.has_receivers,this._error=null,this.api.listReceivers().then(e=>{this._receivers=e}).catch(()=>{this._receivers=[]})}catch(e){this._error=`Failed to load: ${e.message}`}finally{this._loading=!1}}_matchesHairDevice(e){if(!e)return!1;const t=e.toLowerCase();return this._hairDevices.some(e=>e.name.toLowerCase()===t)}async _subscribeLive(){try{this._unsubLive=await this.api.subscribeUnknownSignals(e=>{this._onLiveSignal(e)})}catch{}}async _unsubscribeLive(){this._unsubLive&&(await this._unsubLive(),this._unsubLive=null)}async _subscribeRemoved(){try{this._unsubRemoved=await this.api.subscribeSignalRemoved(e=>{this._load(),this._expandedId===e.device_id&&(e.device_removed?(this._expandedId=null,this._expandedDevice=null):(this._toggleExpand(e.device_id),this._toggleExpand(e.device_id)))})}catch{}}async _unsubscribeRemoved(){this._unsubRemoved&&(await this._unsubRemoved(),this._unsubRemoved=null)}async _subscribeDismissActivity(){try{this._unsubDismiss=await this.api.subscribeDismissActivity(()=>this._onDismissActivity())}catch{}}async _unsubscribeDismissActivity(){this._unsubDismiss&&(await this._unsubDismiss(),this._unsubDismiss=null)}_onDismissActivity(){this._dismissDotVisible=!0,this._dismissGlowActive=!0,null!==this._dismissGlowTimer&&clearTimeout(this._dismissGlowTimer),this._dismissGlowTimer=setTimeout(()=>{this._dismissGlowActive=!1,this._dismissGlowTimer=null},ns.DISMISS_GLOW_HOLD_MS)}_startRename(e,t){t.stopPropagation(),this._editingDeviceId=e.id,this._editLabel=e.label??e.protocol??""}async _commitRename(e){const t=this._editLabel.trim();this._editingDeviceId=null;try{const i=await this.api.renameUnknown(e,t),s=this._devices.findIndex(t=>t.id===e);if(s>=0){const e=[...this._devices];e[s]={...e[s],label:i.label},this._devices=e}}catch(e){this._error=`Rename failed: ${e.message}`}}_cancelRename(){this._editingDeviceId=null}_onRenameKeydown(e,t){"Enter"===t.key?this._commitRename(e):"Escape"===t.key&&this._cancelRename()}_promoteDevice(e,t){t.stopPropagation(),this._promoteTarget=e}_closePromote(){this._promoteTarget=null}async _onDevicePromoted(){this._promoteTarget=null,await this._load()}_openAssign(e,t,i,s){this._assignSignal={deviceId:e,signal:t,label:i??null,initialMode:s??"existing"}}_onAssignClick(e,t,i,s){if(!t.assigned_to?.length)return void this._openAssign(e,t,i);const o=s?.currentTarget,a=o?.getBoundingClientRect();this._assignedPopover={deviceId:e,signal:t,label:i??null,top:a?a.bottom+4:120,left:a?Math.max(8,a.right-220):120},this._installPopoverDismiss()}_closeAssignedPopover(){this._assignedPopover=null,this._removePopoverDismiss()}_onAssignedPopoverCreateNew(){const e=this._assignedPopover;this._closeAssignedPopover(),e&&this._openAssign(e.deviceId,e.signal,e.label)}_onAssignedPopoverOpen(e){const t=e.detail;this._closeAssignedPopover(),t&&this.dispatchEvent(new CustomEvent("navigate-device",{detail:t.device_id,bubbles:!0,composed:!0}))}_closeAssign(){this._assignSignal=null}async _onSignalAssigned(e){if(this._assignSignal=null,await this._load(),this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{this._expandedId=null,this._expandedDevice=null}}_openDelete(e,t){this._deleteSignal={deviceId:e,signal:t}}_closeDelete(){this._deleteSignal=null}_openEditSignal(e,t,i){i.stopPropagation(),this._editSignal={deviceId:e,signal:t}}async _onSignalEdited(){if(this._editSignal=null,await this._load(),this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{this._expandedId=null,this._expandedDevice=null}}async _confirmDelete(){if(!this._deleteSignal)return;const{deviceId:e,signal:t}=this._deleteSignal;this._deleteSignal=null;try{await this.api.deleteSignal(e,t.id),await this._load()}catch(e){this._error=`Delete failed: ${e.message}`}}_openTestDialog(e){this._testDialog={signal:e}}_closeTestDialog(){this._testDialog=null}async _sendTest(e){if(!this._testDialog)return;const{signal:t}=this._testDialog,i=e.detail.emitters;if(0!==i.length){this._testingSignalId=t.id,this._testResult=null,this._testDialog=null;try{const e=(await Promise.allSettled(i.map(e=>this.api.testSignal(t.id,e)))).filter(e=>"fulfilled"===e.status&&e.value.sent).length,s=i.length;this._testResult=e===s?1===s?"Sent!":`Sent! (${e}/${s})`:0===e?"Failed":`Sent (${e}/${s})`}catch{this._testResult="Error"}setTimeout(()=>{this._testResult=null,this._testingSignalId=null},3e3)}}_hasTrigger(e){return this._triggers.some(t=>rs(t,e))}_triggerCountFor(e){return this._triggers.filter(t=>rs(t,e)).length}_openTriggerDialog(e,t,i){const s=this._triggers.filter(e=>rs(e,t));if(0===s.length)return void(this._triggerDialog={signal:t,deviceId:e});const o=i?.currentTarget,a=o?.getBoundingClientRect();this._triggerPopover={deviceId:e,signal:t,top:a?a.bottom+4:120,left:a?Math.max(8,a.right-220):120},this._installPopoverDismiss()}_closeTriggerPopover(){this._triggerPopover=null,this._removePopoverDismiss()}_onPopoverCreateNew(){const e=this._triggerPopover;this._closeTriggerPopover(),e&&(this._triggerDialog={signal:e.signal,deviceId:e.deviceId})}_onPopoverEditTrigger(e){const t=e.detail;this._closeTriggerPopover(),t&&(this._triggerEditDialog=t)}_installPopoverDismiss(){setTimeout(()=>{document.addEventListener("click",this._onDocClickForPopover,!0),window.addEventListener("scroll",this._onScrollForPopover,!0)},0)}_removePopoverDismiss(){document.removeEventListener("click",this._onDocClickForPopover,!0),window.removeEventListener("scroll",this._onScrollForPopover,!0)}async _subscribeUpdated(){try{this._unsubUpdated=await this.api.subscribeSignalUpdated(()=>{this._refreshAfterSignalUpdate()})}catch{}}async _unsubscribeUpdated(){this._unsubUpdated&&(await this._unsubUpdated(),this._unsubUpdated=null)}async _refreshAfterSignalUpdate(){try{this._triggers=await this.api.listTriggers()}catch{}if(this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{}}_closeTriggerDialog(){this._triggerDialog=null,this._triggerEditDialog=null}_requestDeleteTrigger(e){this._confirmDeleteTriggerId=e}async _doDeleteTrigger(){if(!this._confirmDeleteTriggerId)return;const e=this._confirmDeleteTriggerId;this._confirmDeleteTriggerId=null,this._triggerEditDialog=null;try{await this.api.deleteTrigger(e),this._triggers=await this.api.listTriggers()}catch{}}async _onTriggerSaved(){this._triggerDialog=null,this._triggerEditDialog=null;try{this._triggers=await this.api.listTriggers()}catch{}}_onLiveSignal(e){if(e.device_fingerprint===as)return;const t=(new Date).toISOString(),i=this._devices.findIndex(t=>t.id===e.device_id);if(i>=0){{const s={...this._devices[i]};s.hit_count=e.device_hit_count??e.hit_count,s.last_seen=t,1===e.hit_count&&(s.signal_count=(s.signal_count??0)+1);const o=[...this._devices];o[i]=s,this._devices=o}if(this._expandedDevice&&this._expandedId===e.device_id){const i=this._expandedDevice.signals.findIndex(t=>t.id===e.signal_id);if(i>=0){const s={...this._expandedDevice.signals[i]};s.hit_count=e.hit_count,s.last_seen=t;const o=[...this._expandedDevice.signals];o[i]=s,this._expandedDevice={...this._expandedDevice,hit_count:e.device_hit_count??e.hit_count,last_seen:t,signals:o}}else this.api.getUnknownDevice(e.device_id).then(t=>{if(this._expandedId===e.device_id){this._expandedDevice=t;const i=this._devices.findIndex(t=>t.id===e.device_id);if(i>=0){const e={...this._devices[i],signal_count:t.signals.length},s=[...this._devices];s[i]=e,this._devices=s}}}).catch(()=>{})}if(this._flashIds=new Set([...this._flashIds,e.device_id]),setTimeout(()=>{const t=new Set(this._flashIds);t.delete(e.device_id),this._flashIds=t},800),this._flashStats=new Set([...this._flashStats,e.device_id]),setTimeout(()=>{const t=new Set(this._flashStats);t.delete(e.device_id),this._flashStats=t},1500),e.signal_id){const t=[e.signal_id,...this._recentSignalIds.filter(t=>t!==e.signal_id)].slice(0,2);this._recentSignalIds=t,this._glowSignalIds=new Set([...this._glowSignalIds,e.signal_id]),setTimeout(()=>{const t=new Set(this._glowSignalIds);t.delete(e.signal_id),this._glowSignalIds=t},1200),this._hitFlashSignalIds=new Set([...this._hitFlashSignalIds,e.signal_id]),setTimeout(()=>{const t=new Set(this._hitFlashSignalIds);t.delete(e.signal_id),this._hitFlashSignalIds=t},1200)}}else this._load()}_onAliasChanged(e){const{id:t,alias:i}=e.detail;this._expandedDevice&&(this._expandedDevice={...this._expandedDevice,signals:this._expandedDevice.signals.map(e=>e.id===t?{...e,alias:i}:e)})}async _toggleExpand(e){if(this._expandedId===e)return this._expandedId=null,void(this._expandedDevice=null);this._expandedId=e;try{this._expandedDevice=await this.api.getUnknownDevice(e)}catch{this._expandedDevice=null}}async _dismiss(e){try{await this.api.dismissUnknown(e),await this._load(),this._expandedId===e&&(this._expandedId=null,this._expandedDevice=null)}catch(e){this._error=`Dismiss failed: ${e.message}`}}async _undismiss(e){try{await this.api.undismissUnknown(e),await this._load()}catch(e){this._error=`Restore failed: ${e.message}`}}async _doClearAll(){this._confirmClearAll=!1;try{await this.api.clearUnknowns(),this._devices=[],this._expandedId=null,this._expandedDevice=null}catch(e){this._error=`Clear failed: ${e.message}`}}_toggleDismissed(){this._showDismissed=!this._showDismissed,this._dismissDotVisible=!1,this._load()}render(){return B`
            <div class="toolbar">
                <span class="title">
                    <ha-svg-icon .path=${cs}></ha-svg-icon>
                    HAIR Sniffer
                    ${this._loading?"":B`<span class="count"
                              >(${this._devices.length}
                              ${1===this._devices.length?"remote":"remotes"})</span
                          >`}
                </span>
            </div>

            ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

            ${this._loading?B`<div class="loading">Scanning for signals...</div>`:0===this._devices.length?this._hasReceivers?B`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${cs}></ha-svg-icon>
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
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${cs}></ha-svg-icon>
                            <h3>No IR receiver is set up</h3>
                            <p>
                                HAIR has no way to receive IR signals yet, so the
                                Sniffer cannot capture anything.
                            </p>
                            <p class="hint">
                                Set up an ESPHome receiver with the infrared
                                platform, or check Settings, then Devices and
                                Services, to confirm your IR device is adopted.
                            </p>
                        </ha-card>
                    `:B`
                        <div class="device-list">
                            ${Se(this._remotesVersion,Te(this._devices,e=>e.id,e=>this._renderDevice(e)))}
                        </div>
                    `}

            <div class="bottom-bar">
                <button
                    class="action-btn dismiss-btn ${this._dismissGlowActive?"dismiss-glow":""}"
                    title="Restore previously hidden remotes"
                    @click=${this._toggleDismissed}
                >
                    ${this._showDismissed?"Hide Dismissed":"Show Dismissed"}
                    ${this._dismissDotVisible?B`<span class="dismiss-dot" aria-hidden="true"></span>`:""}
                </button>
                ${this._devices.length>0||this._showDismissed?B`<button
                          class="action-btn delete-btn"
                          title="Wipe the entire unknown catalog AND the dismiss list. Use Show Dismissed before Clear All if you want to retain individual dismissed entries."
                          @click=${()=>this._confirmClearAll=!0}
                      >
                          Clear All
                      </button>`:""}
            </div>

            ${this._assignSignal?B`
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

            ${this._promoteTarget?B`
                      <ir-promote-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .suggestedName=${this._promoteTarget.label??""}
                          @device-created=${this._onDevicePromoted}
                          @closed=${this._closePromote}
                      ></ir-promote-dialog>
                  `:""}

            ${this._deleteSignal?B`
                      <ir-confirm-dialog
                          title="Delete Signal"
                          message="Remove this signal permanently? This cannot be undone."
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._confirmDelete}
                          @closed=${this._closeDelete}
                      ></ir-confirm-dialog>
                  `:""}

            ${this._editSignal?B`<ir-signal-editor
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

            ${this._confirmClearAll?B`
                      <ir-confirm-dialog
                          title="Clear All Signals"
                          message="Remove all unknown signals and devices? This cannot be undone."
                          confirmLabel="Clear All"
                          .destructive=${!0}
                          @confirmed=${this._doClearAll}
                          @closed=${()=>this._confirmClearAll=!1}
                      ></ir-confirm-dialog>
                  `:""}

            ${this._triggerPopover?B`
                      <ir-trigger-popover
                          .triggers=${this._triggers.filter(e=>rs(e,this._triggerPopover.signal))}
                          .receivers=${this._receivers}
                          .top=${this._triggerPopover.top}
                          .left=${this._triggerPopover.left}
                          @create-new=${this._onPopoverCreateNew}
                          @edit-trigger=${this._onPopoverEditTrigger}
                      ></ir-trigger-popover>
                  `:""}
            ${this._assignedPopover?B`
                      <ir-assigned-popover
                          .assignments=${this._assignedPopover.signal.assigned_to??[]}
                          .top=${this._assignedPopover.top}
                          .left=${this._assignedPopover.left}
                          @create-new=${this._onAssignedPopoverCreateNew}
                          @open-assignment=${this._onAssignedPopoverOpen}
                      ></ir-assigned-popover>
                  `:""}
            ${this._triggerDialog?B`
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
            ${this._testDialog?B`
                      <ir-test-emitter-dialog
                          .api=${this.api}
                          .hass=${this.hass}
                          .value=${this._testEmitters}
                          @emitters-changed=${e=>this._testEmitters=e.detail.value}
                          @send=${this._sendTest}
                          @closed=${this._closeTestDialog}
                      ></ir-test-emitter-dialog>
                  `:""}
            ${this._triggerEditDialog?B`
                      <ir-trigger-dialog
                          .api=${this.api}
                          .trigger=${this._triggerEditDialog}
                          @trigger-saved=${this._onTriggerSaved}
                          @closed=${this._closeTriggerDialog}
                          @trigger-delete=${e=>this._requestDeleteTrigger(e.detail.triggerId)}
                      ></ir-trigger-dialog>
                  `:""}
            ${this._confirmDeleteTriggerId?B`
                      <ir-confirm-dialog
                          title="Delete Trigger"
                          message="Remove this trigger? The associated HA event entity will also be removed."
                          confirmLabel="Delete"
                          .destructive=${!0}
                          @confirmed=${this._doDeleteTrigger}
                          @closed=${()=>this._confirmDeleteTriggerId=null}
                      ></ir-confirm-dialog>
                  `:""}
        `}_renderDevice(e){const t=this._expandedId===e.id,i=this._flashIds.has(e.id),s=this._flashStats.has(e.id);return B`
            <ha-card class="device ${e.dismissed?"dismissed":""}">
                <div
                    class="device-row ${i?"flash-row":""}"
                    @click=${()=>this._toggleExpand(e.id)}
                >
                    <div class="device-info">
                        <div class="device-header">
                            ${this._editingDeviceId===e.id?B`<input
                                      class="rename-input"
                                      type="text"
                                      .value=${this._editLabel}
                                      @input=${e=>{this._editLabel=e.target.value}}
                                      @keydown=${t=>this._onRenameKeydown(e.id,t)}
                                      @blur=${()=>{this._commitRename(e.id)}}
                                      @click=${e=>e.stopPropagation()}
                                  />`:B`<ha-svg-icon
                                          class="remote-grip"
                                          .path=${hs}
                                          title="Drag to reorder"
                                          @click=${e=>e.stopPropagation()}
                                      ></ha-svg-icon>
                                      ${e.dismissed?B`<span class="protocol locked"
                                                >${e.label??e.protocol??"RAW"}</span
                                            >`:B`<span
                                                class="protocol"
                                                title="Click to rename"
                                                @click=${t=>this._startRename(e,t)}
                                            >${e.label??e.protocol??"RAW"}</span>`}`}
                            <span class="device-stats ${s?"stats-flash":""}">
                                <span class="stat"
                                    ><strong>${e.hit_count}</strong>
                                    ${1===e.hit_count?"hit":"hits"}</span
                                >
                                <span class="stat"
                                    ><strong>${e.signal_count}</strong>
                                    ${1===e.signal_count?"signal":"signals"}</span
                                >
                                <span class="stat last-seen" title=${ls(e.last_seen)}>${ds(e.last_seen)}</span>
                            </span>
                            ${e.label&&this._matchesHairDevice(e.label)?B`<span
                                      class="status-badge hair-device"
                                      @click=${e=>e.stopPropagation()}
                                  >HAIR Device</span>`:e.label&&!e.dismissed?B`<span
                                          class="status-badge promote-badge"
                                          @click=${t=>this._promoteDevice(e,t)}
                                      >Promote</span>`:""}
                            ${e.device_address?B`<span class="address">addr: ${e.device_address}</span>`:""}
                            ${e.dismissed?B`<span class="dismissed-badge">dismissed</span>`:""}
                        </div>
                    </div>
                    ${e.dismissed?B`<button
                              class="action-btn device-dismiss-btn"
                              @click=${t=>{t.stopPropagation(),this._undismiss(e.id)}}
                          >Restore</button>`:B`<button
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
        `}_renderExpanded(e){return B`
            <div class="expanded">
                <div class="signal-header">
                    <span>Signals (${e.signals.length})</span>
                    <span class="first-seen">First seen: ${ls(e.first_seen)}</span>
                </div>
                <div class="signal-list">
                    ${Se(this._signalsVersion,Te(e.signals,e=>e.id,t=>{const i=this._recentSignalIds.indexOf(t.id),s=0===i,o=1===i,a=this._glowSignalIds.has(t.id),r=this._hitFlashSignalIds.has(t.id);return B`
                            <div class="signal-row">
                                ${e.dismissed?"":B`<ha-svg-icon
                                          class="signal-grip"
                                          .path=${hs}
                                          title="Drag to reorder"
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
                                    <span class="${r?"hit-flash":""}"
                                        >${t.hit_count}
                                        ${1===t.hit_count?"hit":"hits"}</span
                                    >
                                    <span title=${ls(t.last_seen)}
                                        >${ds(t.last_seen)}</span
                                    >
                                    <span>${Math.round(t.frequency/1e3)} kHz</span>
                                </div>
                                ${t.code?B`<button
                                          ?disabled=${e.dismissed}
                                          title="View or edit code"
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
                                        class="action-btn assign-btn ${s?"recent-latest":""} ${o?"recent-previous":""} ${a?"glow":""}"
                                        @click=${i=>{i.stopPropagation(),this._onAssignClick(e.id,t,e.label,i)}}
                                        ?disabled=${e.dismissed}
                                        title=${t.assignment_count&&t.assigned_to?.length?1===t.assignment_count?`Assigned to ${t.assigned_to[0].device_name} / ${t.assigned_to[0].command_name}`:`Assigned to ${t.assignment_count} commands:\n- ${t.assigned_to.map(e=>`${e.device_name} / ${e.command_name}`).join("\n- ")}`:e.dismissed?"Restore this remote first":"Assign this signal to a HAIR device"}
                                    >Assign<ir-count-dot
                                            color="green"
                                            .count=${t.assignment_count??0}
                                        ></ir-count-dot></button>
                                    <button
                                        class="action-btn test-btn"
                                        @click=${e=>{e.stopPropagation(),this._openTestDialog(t)}}
                                        ?disabled=${e.dismissed||this._testingSignalId===t.id}
                                        title=${e.dismissed?"Restore this remote first":"Send this signal through an emitter to test it"}
                                    >${this._testingSignalId===t.id?this._testResult??"Sending...":"Test"}</button>
                                    <button
                                        class="action-btn trigger-btn"
                                        @click=${i=>{i.stopPropagation(),this._openTriggerDialog(e.id,t,i)}}
                                        ?disabled=${e.dismissed}
                                        title=${this._hasTrigger(t)?"Edit trigger(s) for this signal":e.dismissed?"Restore this remote first":"Create an HA event entity that fires on this signal"}
                                    >Trigger<ir-count-dot
                                            color="yellow"
                                            .count=${this._triggerCountFor(t)}
                                        ></ir-count-dot></button>
                                    <button
                                        class="action-btn delete-btn"
                                        @click=${i=>{i.stopPropagation(),this._openDelete(e.id,t)}}
                                    >Delete</button>
                                </div>
                            </div>
                        `}))}
                </div>
            </div>
        `}};ps.DISMISS_GLOW_HOLD_MS=3800,ps.styles=[Ei,r`
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
    `],e([he({attribute:!1})],ps.prototype,"api",void 0),e([he({attribute:!1})],ps.prototype,"hass",void 0),e([pe()],ps.prototype,"_devices",void 0),e([pe()],ps.prototype,"_hairDevices",void 0),e([pe()],ps.prototype,"_loading",void 0),e([pe()],ps.prototype,"_error",void 0),e([pe()],ps.prototype,"_hasReceivers",void 0),e([pe()],ps.prototype,"_showDismissed",void 0),e([pe()],ps.prototype,"_expandedId",void 0),e([pe()],ps.prototype,"_expandedDevice",void 0),e([pe()],ps.prototype,"_flashIds",void 0),e([pe()],ps.prototype,"_flashStats",void 0),e([pe()],ps.prototype,"_recentSignalIds",void 0),e([pe()],ps.prototype,"_glowSignalIds",void 0),e([pe()],ps.prototype,"_hitFlashSignalIds",void 0),e([pe()],ps.prototype,"_confirmClearAll",void 0),e([pe()],ps.prototype,"_triggers",void 0),e([pe()],ps.prototype,"_triggerDialog",void 0),e([pe()],ps.prototype,"_triggerEditDialog",void 0),e([pe()],ps.prototype,"_confirmDeleteTriggerId",void 0),e([pe()],ps.prototype,"_triggerPopover",void 0),e([pe()],ps.prototype,"_assignedPopover",void 0),e([pe()],ps.prototype,"_receivers",void 0),e([pe()],ps.prototype,"_editingDeviceId",void 0),e([pe()],ps.prototype,"_editLabel",void 0),e([pe()],ps.prototype,"_promoteTarget",void 0),e([pe()],ps.prototype,"_assignSignal",void 0),e([pe()],ps.prototype,"_deleteSignal",void 0),e([pe()],ps.prototype,"_editSignal",void 0),e([pe()],ps.prototype,"_testingSignalId",void 0),e([pe()],ps.prototype,"_testResult",void 0),e([pe()],ps.prototype,"_testDialog",void 0),e([pe()],ps.prototype,"_testEmitters",void 0),e([pe()],ps.prototype,"_dismissGlowActive",void 0),e([pe()],ps.prototype,"_dismissDotVisible",void 0),e([pe()],ps.prototype,"_remotesVersion",void 0),e([pe()],ps.prototype,"_signalsVersion",void 0),ps=ns=e([ue("ir-signal-monitor")],ps);let gs=class extends ne{constructor(){super(...arguments),this._name="",this._busy=!1,this._error=null,this._brands=[],this._selectedBrand="",this._selectedCodebook="",this._nameEdited=!1}connectedCallback(){super.connectedCallback(),this._loadBrands()}async _loadBrands(){try{this._brands=await this.api.getCodeBrands()}catch{this._brands=[]}}_brand(e){return this._brands.find(t=>t.brand===e)}_codebookLabel(e,t){const i=this._brand(e)?.codebooks.find(e=>e.id===t);return i?.label??""}_maybeAutofillName(){if(this._nameEdited)return;const e=this._brand(this._selectedBrand);if(!e||!this._selectedCodebook)return;const t=this._codebookLabel(this._selectedBrand,this._selectedCodebook);this._name=`${e.label} ${t}`.trim()}_onBrandChange(e){this._selectedBrand=e.target.value;const t=this._brand(this._selectedBrand);t&&1===t.codebooks.length?this._selectedCodebook=t.codebooks[0].id:this._selectedCodebook="",this._maybeAutofillName()}_onCodebookChange(e){this._selectedCodebook=e.target.value,this._maybeAutofillName()}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _create(){if(this._name.trim()){this._busy=!0,this._error=null;try{let e;e=this._selectedCodebook?(await this.api.importCodeRemote(this._selectedCodebook,this._name.trim())).device:await this.api.createRemote(this._name.trim()),this.dispatchEvent(new CustomEvent("remote-created",{detail:e,bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error="Name is required."}_onKeydown(e){"Enter"===e.key&&this._create()}render(){const e=this._brand(this._selectedBrand);return B`
            <ha-dialog
                open
                heading="Create Remote"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                <div class="field">
                    <label>Name</label>
                    <input
                        type="text"
                        .value=${this._name}
                        placeholder="e.g. Living Room TV"
                        required
                        autofocus
                        @input=${e=>{this._name=e.target.value,this._nameEdited=!0}}
                        @keydown=${this._onKeydown}
                    />
                </div>

                ${this._brands.length>0?B`
                          <div class="field">
                              <label>Type</label>
                              <select
                                  .value=${this._selectedBrand}
                                  @change=${this._onBrandChange}
                              >
                                  <option value="">Blank remote</option>
                                  <optgroup label="From code library">
                                      ${this._brands.map(e=>B`<option value=${e.brand}>
                                              ${e.label}
                                          </option>`)}
                                  </optgroup>
                              </select>
                          </div>

                          ${e?B`<div class="field">
                                    <label>Model</label>
                                    <select
                                        .value=${this._selectedCodebook}
                                        @change=${this._onCodebookChange}
                                    >
                                        <option value="">
                                            Select a model
                                        </option>
                                        ${e.codebooks.map(e=>B`<option value=${e.id}>
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
        `}};gs.styles=r`
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
            border-color: #b87333;
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
            background: #b87333;
            color: #fff;
            border-color: #b87333;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `,e([he({attribute:!1})],gs.prototype,"api",void 0),e([pe()],gs.prototype,"_name",void 0),e([pe()],gs.prototype,"_busy",void 0),e([pe()],gs.prototype,"_error",void 0),e([pe()],gs.prototype,"_brands",void 0),e([pe()],gs.prototype,"_selectedBrand",void 0),e([pe()],gs.prototype,"_selectedCodebook",void 0),gs=e([ue("ir-create-remote-dialog")],gs);const us="M12.462,10.448c-0.639-0.639-1.678-0.639-2.317,0c-0.639,0.639-0.639,1.678,0,2.317l1.09,1.09c0.319,0.319,0.739,0.479,1.159,0.479c0.42,0,0.839-0.16,1.159-0.479c0-0,0-0,0-0c0.639-0.639,0.639-1.678,0-2.317L12.462,10.448z M12.763,13.066c-0.204,0.204-0.535,0.204-0.739,0l-1.09-1.09c-0.204-0.204-0.204-0.535,0-0.739c0.102-0.102,0.236-0.153,0.369-0.153c0.134,0,0.267,0.051,0.369,0.153l1.09,1.09C12.966,12.531,12.966,12.863,12.763,13.066z M23.998,6.609l-0.104-1.419c-0.02-0.276-0.24-0.496-0.516-0.516l-0.938-0.068l-0.068-0.938c-0.02-0.276-0.24-0.496-0.516-0.516l-0.938-0.068l-0.069-0.938c-0.02-0.276-0.24-0.496-0.516-0.516l-0.938-0.068l-0.069-0.938c-0.02-0.276-0.24-0.496-0.516-0.516l-1.419-0.103c-0.162-0.012-0.321,0.047-0.435,0.162l-1.993,1.993c-0,0.001-0.001,0.001-0.001,0.001c-0.097,0.097-0.191,0.197-0.282,0.298c-1.933,2.042-12.871,13.598-13.716,14.551c-0.722,0.814-0.712,1.983,0.023,2.717l0.341,0.341L0.539,20.852c-0.719,0.719-0.719,1.889,0,2.609c0.36,0.36,0.832,0.539,1.304,0.539c0.472,0,0.945-0.18,1.304-0.539l0.787-0.787l0.341,0.341c0.735,0.735,1.903,0.745,2.717,0.023c0.953-0.845,12.509-11.783,14.551-13.716c0.102-0.091,0.201-0.186,0.299-0.283c0.001-0.001,0.001-0.001,0.001-0.002l1.992-1.992C23.951,6.93,24.01,6.771,23.998,6.609z M20.61,4.179l0.684,0.05l0.05,0.684l-1.418,1.418l-0.733-0.734L20.61,4.179z M19.087,2.656l0.684,0.05l0.05,0.684L18.403,4.807L17.67,4.074L19.087,2.656z M17.564,1.133l0.684,0.05l0.05,0.684l-1.418,1.418l-0.733-0.733L17.564,1.133z M2.359,22.671c-0.284,0.284-0.746,0.284-1.03,0c-0.284-0.284-0.284-0.746,0-1.03l0.787-0.787l1.03,1.03L2.359,22.671z M6.253,22.202c-0.366,0.324-0.877,0.334-1.188,0.023l-0.735-0.735l-2.555-2.555c-0.311-0.311-0.301-0.822,0.023-1.188c0.633-0.715,7.3-7.769,11.189-11.88c-0.014,0.084-0.026,0.169-0.036,0.253c-0.179,1.482,0.239,2.815,1.176,3.752c0.937,0.937,2.27,1.355,3.752,1.176c0.084-0.01,0.169-0.022,0.253-0.036C14.022,14.901,6.968,21.568,6.253,22.202z M14.917,9.083c-0.69-0.69-0.994-1.694-0.857-2.829c0.123-1.019,0.585-2.03,1.315-2.897l0.717,0.717l-0.879,0.879c-0.218,0.218-0.218,0.571,0,0.789c0.218,0.218,0.571,0.218,0.789,0l0.879-0.879l0.734,0.734l-0.879,0.879c-0.218,0.218-0.218,0.571,0,0.789c0.218,0.218,0.571,0.218,0.789,0l0.879-0.879l0.734,0.734l-0.879,0.879c-0.218,0.218-0.218,0.571,0,0.789c0.218,0.218,0.571,0.218,0.789,0l0.879-0.879l0.717,0.717C18.756,10.213,16.277,10.443,14.917,9.083z M21.449,7.853l-0.734-0.734l1.418-1.418l0.684,0.05l0.05,0.684L21.449,7.853z",ms="M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z";let vs=class extends ne{constructor(){super(...arguments),this._devices=[],this._hairDevices=[],this._triggers=[],this._loading=!0,this._error=null,this._expandedId=null,this._expandedDevice=null,this._confirmClearAll=!1,this._deleteRemoteId=null,this._deleteRemoteLabel="",this._deleteRemoteCount=0,this._editingDeviceId=null,this._editLabel="",this._createRemoteOpen=!1,this._createSignalDeviceId=null,this._editSignal=null,this._promoteTarget=null,this._assignSignal=null,this._deleteSignal=null,this._triggerDialog=null,this._triggerEditDialog=null,this._triggerPopover=null,this._assignedPopover=null,this._receivers=[],this._unsubUpdated=null,this._confirmDeleteTriggerId=null,this._testDialog=null,this._testEmitters=[],this._testingSignalId=null,this._testResult=null,this._remotesVersion=0,this._signalsVersion=0,this._remotesSortable=null,this._signalsSortable=null,this._signalsSortableContainer=null,this._pendingRemotesSave=null,this._pendingSignalsSave=null,this._onDocClickForPopover=e=>{const t=e.composedPath(),i=this.shadowRoot?.querySelector("ir-trigger-popover"),s=this.shadowRoot?.querySelector("ir-assigned-popover");i&&t.includes(i)||s&&t.includes(s)||(this._closeTriggerPopover(),this._closeAssignedPopover())},this._onScrollForPopover=()=>{this._closeTriggerPopover(),this._closeAssignedPopover()}}connectedCallback(){super.connectedCallback(),this._load(),this._subscribeUpdated()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeUpdated(),this._removePopoverDismiss(),this._remotesSortable?.destroy(),this._remotesSortable=null,this._signalsSortable?.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null,null!==this._pendingRemotesSave&&clearTimeout(this._pendingRemotesSave),null!==this._pendingSignalsSave&&clearTimeout(this._pendingSignalsSave)}updated(e){if(super.updated(e),e.has("_editingDeviceId")&&this._editingDeviceId){const e=this.shadowRoot?.querySelector(".rename-input");e?.focus(),e?.select()}this._syncSortables()}_syncSortables(){const e=this.renderRoot.querySelector(".device-list");e&&!this._remotesSortable?this._attachRemotesSortable(e):!e&&this._remotesSortable&&(this._remotesSortable.destroy(),this._remotesSortable=null);const t=this.renderRoot.querySelector(".signal-list"),i=!!this._expandedDevice&&!this._expandedDevice.dismissed;!t||!i||this._signalsSortable&&this._signalsSortableContainer===t?t&&i||!this._signalsSortable||(this._signalsSortable.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null):(this._signalsSortable?.destroy(),this._attachSignalsSortable(t))}_attachRemotesSortable(e){this._remotesSortable=di.create(e,{handle:".remote-grip",animation:150,ghostClass:"sortable-ghost",onEnd:t=>{const{oldIndex:i,newIndex:s}=t;if(void 0===i||void 0===s||i===s)return;const o=[...this._devices],[a]=o.splice(i,1);o.splice(s,0,a),this._devices=o,this._remotesSortable?.destroy(),this._remotesSortable=null,this._purgeChildren(e,"ha-card"),this._remotesVersion++,this._scheduleRemotesSave(o.map(e=>e.id))}})}_attachSignalsSortable(e){this._expandedDevice&&(this._signalsSortableContainer=e,this._signalsSortable=di.create(e,{handle:".signal-grip",animation:150,ghostClass:"sortable-ghost",onEnd:t=>{const{oldIndex:i,newIndex:s}=t;if(void 0===i||void 0===s||i===s)return;const o=this._expandedDevice;if(!o)return;const a=[...o.signals],[r]=a.splice(i,1);a.splice(s,0,r),this._expandedDevice={...o,signals:a},this._signalsSortable?.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null,this._purgeChildren(e,".signal-row"),this._signalsVersion++,this._scheduleSignalsSave(o.id,a.map(e=>e.id))}}))}_purgeChildren(e,t){for(const i of Array.from(e.querySelectorAll(t)))i.remove()}_scheduleRemotesSave(e){null!==this._pendingRemotesSave&&clearTimeout(this._pendingRemotesSave),this._pendingRemotesSave=window.setTimeout(async()=>{this._pendingRemotesSave=null;try{await this.api.reorderUnknownDevices("manual",e)}catch(e){this._error=`Reorder failed: ${e.message}`,await this._load()}},500)}_scheduleSignalsSave(e,t){null!==this._pendingSignalsSave&&clearTimeout(this._pendingSignalsSave),this._pendingSignalsSave=window.setTimeout(async()=>{this._pendingSignalsSave=null;try{await this.api.reorderUnknownSignals(e,t)}catch(e){this._error=`Reorder failed: ${e.message}`,await this._refreshExpanded()}},500)}async _load(){this._loading=!0;try{const[e,t,i]=await Promise.all([this.api.getUnknownDevices({include_dismissed:!0,min_hits:0,source:"manual"}),this.api.listDevices(),this.api.listTriggers()]);this._devices=e,this._hairDevices=t,this._triggers=i,this._error=null,this.api.listReceivers().then(e=>{this._receivers=e}).catch(()=>{this._receivers=[]})}catch(e){this._error=`Failed to load: ${e.message}`}finally{this._loading=!1}}_matchesHairDevice(e){if(!e)return!1;const t=e.toLowerCase();return this._hairDevices.some(e=>e.name.toLowerCase()===t)}async _refreshExpanded(){if(this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{this._expandedId=null,this._expandedDevice=null}}openCreateRemote(){this._createRemoteOpen=!0}async _onRemoteCreated(e){this._createRemoteOpen=!1,await this._load(),this._expandedId=e.detail.id,await this._refreshExpanded()}_openCreateSignal(e,t){t.stopPropagation(),this._createSignalDeviceId=e}async _onSignalCreated(){this._createSignalDeviceId=null,await this._refreshExpanded(),await this._load()}_openEditSignal(e,t,i){i.stopPropagation(),this._editSignal={deviceId:e,signal:t}}async _onSignalEdited(){this._editSignal=null,await this._refreshExpanded(),await this._load()}_openDeleteRemote(e){this._deleteRemoteId=e.id,this._deleteRemoteLabel=e.label||"this remote",this._deleteRemoteCount=e.signals.length}async _confirmDeleteRemote(){const e=this._deleteRemoteId;if(this._deleteRemoteId=null,e)try{await this.api.deleteRemote(e),this._expandedId===e&&(this._expandedId=null,this._expandedDevice=null),await this._load()}catch(e){this._error=`Delete failed: ${e.message}`}}_onAliasChanged(e){const{id:t,alias:i}=e.detail;this._expandedDevice&&(this._expandedDevice={...this._expandedDevice,signals:this._expandedDevice.signals.map(e=>e.id===t?{...e,alias:i}:e)})}_startRename(e,t){t.stopPropagation(),this._editingDeviceId=e.id,this._editLabel=e.label??""}async _commitRename(e){const t=this._editLabel.trim();this._editingDeviceId=null;try{const i=await this.api.renameUnknown(e,t),s=this._devices.findIndex(t=>t.id===e);if(s>=0){const e=[...this._devices];e[s]={...e[s],label:i.label},this._devices=e}}catch(e){this._error=`Rename failed: ${e.message}`}}_onRenameKeydown(e,t){"Enter"===t.key?this._commitRename(e):"Escape"===t.key&&(this._editingDeviceId=null)}_promoteDevice(e,t){t.stopPropagation(),this._promoteTarget=e}async _onDevicePromoted(){this._promoteTarget=null,await this._load()}_openAssign(e,t,i){this._assignSignal={deviceId:e,signal:t,label:i??null}}_onAssignClick(e,t,i,s){if(!t.assigned_to?.length)return void this._openAssign(e,t,i);const o=s?.currentTarget,a=o?.getBoundingClientRect();this._assignedPopover={deviceId:e,signal:t,label:i??null,top:a?a.bottom+4:120,left:a?Math.max(8,a.right-220):120},this._installPopoverDismiss()}_closeAssignedPopover(){this._assignedPopover=null,this._removePopoverDismiss()}_onAssignedPopoverCreateNew(){const e=this._assignedPopover;this._closeAssignedPopover(),e&&this._openAssign(e.deviceId,e.signal,e.label)}_onAssignedPopoverOpen(e){const t=e.detail;this._closeAssignedPopover(),t&&this.dispatchEvent(new CustomEvent("navigate-device",{detail:t.device_id,bubbles:!0,composed:!0}))}async _onSignalAssigned(e){this._assignSignal=null,await this._load(),await this._refreshExpanded()}_openDelete(e,t){this._deleteSignal={deviceId:e,signal:t}}async _confirmDelete(){if(!this._deleteSignal)return;const{deviceId:e,signal:t}=this._deleteSignal;this._deleteSignal=null;try{await this.api.deleteSignal(e,t.id),await this._load(),await this._refreshExpanded()}catch(e){this._error=`Delete failed: ${e.message}`}}_openTestDialog(e){this._testDialog={signal:e}}async _sendTest(e){if(!this._testDialog)return;const{signal:t}=this._testDialog,i=e.detail.emitters;if(0!==i.length){this._testingSignalId=t.id,this._testResult=null,this._testDialog=null;try{const e=(await Promise.allSettled(i.map(e=>this.api.testSignal(t.id,e)))).filter(e=>"fulfilled"===e.status&&e.value.sent).length,s=i.length;this._testResult=e===s?1===s?"Sent!":`Sent! (${e}/${s})`:0===e?"Failed":`Sent (${e}/${s})`}catch{this._testResult="Error"}setTimeout(()=>{this._testResult=null,this._testingSignalId=null},3e3)}}_hasTrigger(e){return this._triggers.some(t=>rs(t,e))}_triggerCountFor(e){return this._triggers.filter(t=>rs(t,e)).length}_openTriggerDialog(e,t,i){const s=this._triggers.filter(e=>rs(e,t));if(0===s.length)return void(this._triggerDialog={signal:t,deviceId:e});const o=i?.currentTarget,a=o?.getBoundingClientRect();this._triggerPopover={deviceId:e,signal:t,top:a?a.bottom+4:120,left:a?Math.max(8,a.right-220):120},this._installPopoverDismiss()}_closeTriggerPopover(){this._triggerPopover=null,this._removePopoverDismiss()}_onPopoverCreateNew(){const e=this._triggerPopover;this._closeTriggerPopover(),e&&(this._triggerDialog={signal:e.signal,deviceId:e.deviceId})}_onPopoverEditTrigger(e){const t=e.detail;this._closeTriggerPopover(),t&&(this._triggerEditDialog=t)}_installPopoverDismiss(){setTimeout(()=>{document.addEventListener("click",this._onDocClickForPopover,!0),window.addEventListener("scroll",this._onScrollForPopover,!0)},0)}_removePopoverDismiss(){document.removeEventListener("click",this._onDocClickForPopover,!0),window.removeEventListener("scroll",this._onScrollForPopover,!0)}async _subscribeUpdated(){try{this._unsubUpdated=await this.api.subscribeSignalUpdated(()=>{this._refreshAfterSignalUpdate()})}catch{}}async _unsubscribeUpdated(){this._unsubUpdated&&(await this._unsubUpdated(),this._unsubUpdated=null)}async _refreshAfterSignalUpdate(){try{this._triggers=await this.api.listTriggers()}catch{}if(this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{}}_closeTriggerDialog(){this._triggerDialog=null,this._triggerEditDialog=null}_requestDeleteTrigger(e){this._confirmDeleteTriggerId=e}async _doDeleteTrigger(){if(!this._confirmDeleteTriggerId)return;const e=this._confirmDeleteTriggerId;this._confirmDeleteTriggerId=null,this._triggerEditDialog=null;try{await this.api.deleteTrigger(e),this._triggers=await this.api.listTriggers()}catch{}}async _onTriggerSaved(){this._triggerDialog=null,this._triggerEditDialog=null;try{this._triggers=await this.api.listTriggers()}catch{}}async _toggleExpand(e){if(this._expandedId===e)return this._expandedId=null,void(this._expandedDevice=null);this._expandedId=e,await this._refreshExpanded()}async _doClearAll(){this._confirmClearAll=!1;try{await this.api.clearUnknowns("manual"),this._devices=[],this._expandedId=null,this._expandedDevice=null}catch(e){this._error=`Clear failed: ${e.message}`}}render(){const e=this._devices.length;return B`
            <div class="toolbar">
                <span class="title">
                    <ha-svg-icon .path=${us}></ha-svg-icon>
                    HAIR Clipper
                    ${this._loading?"":B`<span class="count"
                              >(${e} ${1===e?"remote":"remotes"})</span
                          >`}
                </span>
                <div class="toolbar-actions">
                    <button
                        class="create-btn"
                        @click=${()=>this._createRemoteOpen=!0}
                    >
                        + Add Remote
                    </button>
                </div>
            </div>

            ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

            ${this._loading?B`<div class="loading">Loading...</div>`:0===e?B`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${us}></ha-svg-icon>
                            <h3>No virtual remotes yet</h3>
                            <p>
                                Clipper lets you build remotes by pasting Pronto codes.
                                Create a remote, then add a signal for each button.
                            </p>
                            <p class="hint">
                                Click "+ Add Remote" above to start a clipped remote.
                            </p>
                        </ha-card>
                    `:B`
                        <div class="device-list">
                            ${Se(this._remotesVersion,Te(this._devices,e=>e.id,e=>this._renderDevice(e)))}
                        </div>
                    `}

            ${e>0?B`
                      <div class="clear-all-row">
                          <button
                              class="action-btn delete-btn"
                              title="Delete all clipped remotes and their signals. Sniffed signals are untouched."
                              @click=${()=>this._confirmClearAll=!0}
                          >
                              Clear All
                          </button>
                      </div>
                  `:""}

            ${this._renderDialogs()}
        `}_renderDevice(e){const t=this._expandedId===e.id;return B`
            <ha-card class="device clip-device">
                <div class="device-row" @click=${()=>this._toggleExpand(e.id)}>
                    <div class="device-info">
                        <div class="device-header">
                            ${this._editingDeviceId===e.id?B`<input
                                      class="rename-input"
                                      type="text"
                                      .value=${this._editLabel}
                                      @input=${e=>{this._editLabel=e.target.value}}
                                      @keydown=${t=>this._onRenameKeydown(e.id,t)}
                                      @blur=${()=>{this._commitRename(e.id)}}
                                      @click=${e=>e.stopPropagation()}
                                  />`:B`<ha-svg-icon
                                          class="remote-grip"
                                          .path=${ms}
                                          title="Drag to reorder"
                                          @click=${e=>e.stopPropagation()}
                                      ></ha-svg-icon>
                                      <span
                                          class="protocol"
                                          title="Click to rename"
                                          @click=${t=>this._startRename(e,t)}
                                          >${e.label??"Remote"}</span
                                      >`}
                            <span class="stat"
                                ><strong>${e.signal_count}</strong>
                                ${1===e.signal_count?"signal":"signals"}</span
                            >
                            ${e.label&&this._matchesHairDevice(e.label)?B`<span
                                      class="status-badge hair-device"
                                      @click=${e=>e.stopPropagation()}
                                  >HAIR Device</span>`:e.label?B`<span
                                          class="status-badge promote-badge"
                                          @click=${t=>this._promoteDevice(e,t)}
                                      >Promote</span>`:""}
                        </div>
                    </div>
                    <ha-svg-icon
                        class="expand-icon"
                        .path=${t?"M7.41,15.41L12,10.83L16.59,15.41L18,14L12,8L6,14L7.41,15.41Z":"M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z"}
                    ></ha-svg-icon>
                </div>

                ${t&&this._expandedDevice?this._renderExpanded(this._expandedDevice):""}
            </ha-card>
        `}_renderExpanded(e){return B`
            <div class="expanded">
                <div class="signal-header">
                    <span>Signals (${e.signals.length})</span>
                    <button
                        class="create-btn create-signal-btn"
                        title="Add a signal to this remote"
                        @click=${t=>this._openCreateSignal(e.id,t)}
                    >
                        + Add Signal
                    </button>
                </div>
                ${0===e.signals.length?B`<div class="no-signals-row">
                          <span class="no-signals"
                              >No signals yet. Click "+ Add Signal" to paste a
                              Pronto code.</span
                          >
                      </div>`:B`
                          <div class="signal-list">
                              ${Se(this._signalsVersion,Te(e.signals,e=>e.id,t=>this._renderSignal(e.id,t,e.label)))}
                          </div>
                      `}
                <div class="remote-footer">
                    <button
                        class="action-btn delete-btn"
                        title="Delete this remote and all its signals"
                        @click=${t=>{t.stopPropagation(),this._openDeleteRemote(e)}}
                    >Delete remote</button>
                </div>
            </div>
        `}_renderSignal(e,t,i){const s=this._testingSignalId===t.id;return B`
            <div class="signal-row">
                <ha-svg-icon
                    class="signal-grip"
                    .path=${ms}
                    title="Drag to reorder"
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
                    ${s&&this._testResult?B`<span class="test-result">${this._testResult}</span>`:B`<span>${Math.round(t.frequency/1e3)} kHz</span>`}
                </div>
                ${t.code?B`<button
                          title="View or edit code"
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
                        title=${t.assignment_count&&t.assigned_to?.length?1===t.assignment_count?`Assigned to ${t.assigned_to[0].device_name} / ${t.assigned_to[0].command_name}`:`Assigned to ${t.assignment_count} commands:\n- ${t.assigned_to.map(e=>`${e.device_name} / ${e.command_name}`).join("\n- ")}`:"Assign this signal to a HAIR device"}
                        @click=${s=>{s.stopPropagation(),this._onAssignClick(e,t,i,s)}}
                    >Assign<ir-count-dot
                            color="green"
                            .count=${t.assignment_count??0}
                        ></ir-count-dot></button>
                    <button
                        class="action-btn test-btn"
                        ?disabled=${s}
                        title="Send this signal through an emitter"
                        @click=${e=>{e.stopPropagation(),this._openTestDialog(t)}}
                    >${s?"Sending...":"Test"}</button>
                    <button
                        class="action-btn trigger-btn"
                        title=${this._hasTrigger(t)?"Edit trigger(s) for this signal":"Create an HA event entity that fires on this signal"}
                        @click=${i=>{i.stopPropagation(),this._openTriggerDialog(e,t,i)}}
                    >Trigger<ir-count-dot
                            color="yellow"
                            .count=${this._triggerCountFor(t)}
                        ></ir-count-dot></button>
                    <button
                        class="action-btn delete-btn"
                        @click=${i=>{i.stopPropagation(),this._openDelete(e,t)}}
                    >Delete</button>
                </div>
            </div>
        `}_renderDialogs(){return B`
            ${this._createRemoteOpen?B`<ir-create-remote-dialog
                      .api=${this.api}
                      @remote-created=${this._onRemoteCreated}
                      @closed=${()=>this._createRemoteOpen=!1}
                  ></ir-create-remote-dialog>`:""}

            ${this._createSignalDeviceId?B`<ir-signal-editor
                      .api=${this.api}
                      .deviceId=${this._createSignalDeviceId}
                      @signal-created=${this._onSignalCreated}
                      @closed=${()=>this._createSignalDeviceId=null}
                  ></ir-signal-editor>`:""}

            ${this._editSignal?B`<ir-signal-editor
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

            ${this._assignSignal?B`<ir-assign-signal-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .unknownDeviceId=${this._assignSignal.deviceId}
                      .signal=${this._assignSignal.signal}
                      .suggestedDeviceName=${this._assignSignal.label??""}
                      .initialMode=${"existing"}
                      @signal-assigned=${this._onSignalAssigned}
                      @closed=${()=>this._assignSignal=null}
                  ></ir-assign-signal-dialog>`:""}

            ${this._promoteTarget?B`<ir-promote-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .suggestedName=${this._promoteTarget.label??""}
                      @device-created=${this._onDevicePromoted}
                      @closed=${()=>this._promoteTarget=null}
                  ></ir-promote-dialog>`:""}

            ${this._deleteSignal?B`<ir-confirm-dialog
                      title="Delete Signal"
                      message="Remove this signal permanently? This cannot be undone."
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._confirmDelete}
                      @closed=${()=>this._deleteSignal=null}
                  ></ir-confirm-dialog>`:""}

            ${this._confirmClearAll?B`<ir-confirm-dialog
                      title="Clear All Clips"
                      message="Remove all clipped remotes and their signals? This cannot be undone. Sniffed signals are not affected."
                      confirmLabel="Clear All"
                      .destructive=${!0}
                      @confirmed=${this._doClearAll}
                      @closed=${()=>this._confirmClearAll=!1}
                  ></ir-confirm-dialog>`:""}

            ${this._deleteRemoteId?B`<ir-confirm-dialog
                      title="Delete Remote"
                      message=${this._deleteRemoteCount>0?`Remove "${this._deleteRemoteLabel}" and its ${this._deleteRemoteCount} ${1===this._deleteRemoteCount?"signal":"signals"}? This cannot be undone.`:`Remove "${this._deleteRemoteLabel}"? This cannot be undone.`}
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._confirmDeleteRemote}
                      @closed=${()=>this._deleteRemoteId=null}
                  ></ir-confirm-dialog>`:""}

            ${this._triggerPopover?B`<ir-trigger-popover
                      .triggers=${this._triggers.filter(e=>rs(e,this._triggerPopover.signal))}
                      .receivers=${this._receivers}
                      .top=${this._triggerPopover.top}
                      .left=${this._triggerPopover.left}
                      @create-new=${this._onPopoverCreateNew}
                      @edit-trigger=${this._onPopoverEditTrigger}
                  ></ir-trigger-popover>`:""}

            ${this._assignedPopover?B`<ir-assigned-popover
                      .assignments=${this._assignedPopover.signal.assigned_to??[]}
                      .top=${this._assignedPopover.top}
                      .left=${this._assignedPopover.left}
                      @create-new=${this._onAssignedPopoverCreateNew}
                      @open-assignment=${this._onAssignedPopoverOpen}
                  ></ir-assigned-popover>`:""}

            ${this._triggerDialog?B`<ir-trigger-dialog
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

            ${this._triggerEditDialog?B`<ir-trigger-dialog
                      .api=${this.api}
                      .trigger=${this._triggerEditDialog}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                      @trigger-delete=${e=>this._requestDeleteTrigger(e.detail.triggerId)}
                  ></ir-trigger-dialog>`:""}

            ${this._confirmDeleteTriggerId?B`<ir-confirm-dialog
                      title="Delete Trigger"
                      message="Remove this trigger? The associated HA event entity will also be removed."
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._doDeleteTrigger}
                      @closed=${()=>this._confirmDeleteTriggerId=null}
                  ></ir-confirm-dialog>`:""}

            ${this._testDialog?B`<ir-test-emitter-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .value=${this._testEmitters}
                      @emitters-changed=${e=>this._testEmitters=e.detail.value}
                      @send=${this._sendTest}
                      @closed=${()=>this._testDialog=null}
                  ></ir-test-emitter-dialog>`:""}
        `}};vs.styles=[Ei,r`
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
        .create-btn {
            background: none;
            color: #b87333;
            border: 1px solid #b87333;
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 0.75rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            transition: background 150ms ease;
        }
        .create-btn:hover:not(:disabled) {
            background: rgba(184, 115, 51, 0.08);
        }
        .create-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        /* Card-internal "+ Add Signal" -- borderless copper text action
           sitting just right of the "Signals (N)" label, so it reads as a
           lighter sibling of the bordered "Add Remote" / "Add Device"
           top-right buttons. No pill, no stroke; slightly larger than the
           old pill label. */
        .create-signal-btn {
            border: none;
            background: none;
            padding: 0;
            font-size: 0.64rem;
            position: relative;
            top: 1px;
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
    `],e([he({attribute:!1})],vs.prototype,"api",void 0),e([he({attribute:!1})],vs.prototype,"hass",void 0),e([pe()],vs.prototype,"_devices",void 0),e([pe()],vs.prototype,"_hairDevices",void 0),e([pe()],vs.prototype,"_triggers",void 0),e([pe()],vs.prototype,"_loading",void 0),e([pe()],vs.prototype,"_error",void 0),e([pe()],vs.prototype,"_expandedId",void 0),e([pe()],vs.prototype,"_expandedDevice",void 0),e([pe()],vs.prototype,"_confirmClearAll",void 0),e([pe()],vs.prototype,"_deleteRemoteId",void 0),e([pe()],vs.prototype,"_deleteRemoteLabel",void 0),e([pe()],vs.prototype,"_deleteRemoteCount",void 0),e([pe()],vs.prototype,"_editingDeviceId",void 0),e([pe()],vs.prototype,"_editLabel",void 0),e([pe()],vs.prototype,"_createRemoteOpen",void 0),e([pe()],vs.prototype,"_createSignalDeviceId",void 0),e([pe()],vs.prototype,"_editSignal",void 0),e([pe()],vs.prototype,"_promoteTarget",void 0),e([pe()],vs.prototype,"_assignSignal",void 0),e([pe()],vs.prototype,"_deleteSignal",void 0),e([pe()],vs.prototype,"_triggerDialog",void 0),e([pe()],vs.prototype,"_triggerEditDialog",void 0),e([pe()],vs.prototype,"_triggerPopover",void 0),e([pe()],vs.prototype,"_assignedPopover",void 0),e([pe()],vs.prototype,"_receivers",void 0),e([pe()],vs.prototype,"_confirmDeleteTriggerId",void 0),e([pe()],vs.prototype,"_testDialog",void 0),e([pe()],vs.prototype,"_testEmitters",void 0),e([pe()],vs.prototype,"_testingSignalId",void 0),e([pe()],vs.prototype,"_testResult",void 0),e([pe()],vs.prototype,"_remotesVersion",void 0),e([pe()],vs.prototype,"_signalsVersion",void 0),vs=e([ue("ir-clips")],vs);let _s=class extends ne{constructor(){super(...arguments),this.pendingEntity="",this._candidates=[],this._entityId="",this._appliance="",this._name="",this._busy=!1,this._loading=!0,this._error=null,this._nameEdited=!1}connectedCallback(){super.connectedCallback(),this._loadVendors()}async _loadVendors(){this._loading=!0;try{const{vendors:e}=await this.api.listPluckVendors();this._candidates=this._flatten(e);const t=this._candidates.find(e=>e.entityId===this.pendingEntity)??(1===this._candidates.length?this._candidates[0]:void 0);t&&(this._entityId=t.entityId,this._autofillName())}catch(e){this._error=e.message,this._candidates=[]}finally{this._loading=!1}}_flatten(e){const t=[];for(const i of e)for(const e of i.blasters)t.push({integration:i.integration,entityId:e.entity_id,vendorName:i.name,blasterName:e.name,applianceLabel:i.appliance_label||"Appliance",applianceHelp:i.appliance_help||""});return t}get _selected(){return this._candidates.find(e=>e.entityId===this._entityId)}_autofillName(){if(this._nameEdited)return;const e=this._selected;if(!e)return;const t=this._appliance.trim();this._name=(t?`${e.blasterName}: ${t}`:e.blasterName).trim()}_onVendorChange(e){this._entityId=e.target.value,this._autofillName()}_onApplianceInput(e){this._appliance=e.target.value,this._autofillName()}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _create(){const e=this._selected;if(e)if(this._appliance.trim())if(this._name.trim()){this._busy=!0,this._error=null;try{const t=await this.api.createPluckedBlaster({vendor_entity_id:e.entityId,appliance:this._appliance.trim(),name:this._name.trim()});this.dispatchEvent(new CustomEvent("blaster-created",{detail:t,bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error="Name is required.";else this._error="Appliance is required.";else this._error="Pick a blaster to pluck from."}render(){const e=this._selected;return B`
            <ha-dialog
                open
                heading="Add Blaster"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

                ${this._loading?B`<div class="muted">Loading blasters...</div>`:0===this._candidates.length?B`<div class="muted">
                            No compatible blasters found. Install a supported IR
                            integration (such as Tuya Local) and learn a code
                            first.
                        </div>`:B`
                            <div class="field">
                                <label>Pluck from</label>
                                <select
                                    .value=${this._entityId}
                                    @change=${this._onVendorChange}
                                >
                                    <option value="">Select a blaster</option>
                                    ${this._candidates.map(e=>B`<option
                                            value=${e.entityId}
                                        >
                                            ${e.vendorName}: ${e.blasterName}
                                        </option>`)}
                                </select>
                            </div>

                            <div class="field">
                                <label>${e?.applianceLabel??"Appliance"}</label>
                                <input
                                    type="text"
                                    .value=${this._appliance}
                                    placeholder="e.g. candles"
                                    required
                                    @input=${this._onApplianceInput}
                                />
                                ${e?.applianceHelp?B`<div class="help">
                                          ${e.applianceHelp}
                                      </div>`:""}
                            </div>

                            <div class="field">
                                <label>Name</label>
                                <input
                                    type="text"
                                    .value=${this._name}
                                    placeholder="e.g. Living Room candles"
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
                        Cancel
                    </button>
                    <button
                        class="action-btn create-btn"
                        @click=${this._create}
                        ?disabled=${this._busy||0===this._candidates.length}
                    >
                        ${this._busy?"Creating...":"Create"}
                    </button>
                </div>
            </ha-dialog>
        `}};_s.styles=r`
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
            border-color: #455a64;
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
            background: #455a64;
            color: #fff;
            border-color: #455a64;
        }
        .create-btn:hover:not(:disabled) {
            opacity: 0.9;
        }
    `,e([he({attribute:!1})],_s.prototype,"api",void 0),e([he()],_s.prototype,"pendingEntity",void 0),e([pe()],_s.prototype,"_candidates",void 0),e([pe()],_s.prototype,"_entityId",void 0),e([pe()],_s.prototype,"_appliance",void 0),e([pe()],_s.prototype,"_name",void 0),e([pe()],_s.prototype,"_busy",void 0),e([pe()],_s.prototype,"_loading",void 0),e([pe()],_s.prototype,"_error",void 0),_s=e([ue("ir-pluck-add-remote-dialog")],_s);let bs=class extends ne{constructor(){super(...arguments),this.integration="",this._commandName="",this._busy=!1,this._creating=!1,this._error=null,this._captures=null,this._aliases=[],this._validations=[]}_close(){this.dispatchEvent(new CustomEvent("closed",{bubbles:!0,composed:!0}))}async _pluck(){const e=this._commandName.trim();if(e){this._busy=!0,this._error=null;try{const t=await this.api.runPluck({integration:this.integration,vendor_entity_id:this.blaster.vendor_entity_id??"",appliance:this.blaster.appliance??"",command_name:e});t.error?this._error=t.message??"Pluck failed.":t.signals&&t.signals.length>0?(this._captures=t.signals,this._aliases=t.signals.map(e=>e.suggested_alias),this._validations=await Promise.all(t.signals.map(e=>this.api.validatePronto(e.code??"").catch(()=>null)))):this._error="No response from blaster. Try again."}catch(e){this._error=e.message}finally{this._busy=!1}}else this._error="Command name is required."}_removeCapture(e){this._captures&&(this._captures=this._captures.filter((t,i)=>i!==e),this._aliases=this._aliases.filter((t,i)=>i!==e),this._validations=this._validations.filter((t,i)=>i!==e),0===this._captures.length&&(this._captures=null))}async _create(){if(this._captures&&0!==this._captures.length){this._creating=!0,this._error=null;try{const e=[];for(let t=0;t<this._captures.length;t++){const i=this._captures[t],s=await this.api.createPluckedSignal({device_id:this.blaster.id,pronto:i.code??"",command_name:i.plucked_command_name,alias:this._aliases[t].trim()});e.push(s)}this.dispatchEvent(new CustomEvent("signals-created",{detail:e,bubbles:!0,composed:!0}))}catch(e){this._error=e.message}finally{this._creating=!1}}}_renderValid(e,t){const i=this._validations[t]??null,s=i?.recognized_protocol??e.decoded_protocol??null,o=null!=i?.frequency_khz?i.frequency_khz.toFixed(1):(e.frequency/1e3).toFixed(1),a=i?.burst_pair_count??null;return B`
            <div class="valid-box">
                <div class="valid-head">
                    <ha-svg-icon .path=${"M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z"}></ha-svg-icon>
                    ${s?`Recognized as ${s}`:"Valid Pronto code"}
                </div>
                <div class="valid-sub">
                    ${o} kHz${null!=a?` · ${a} burst pairs`:""}
                </div>
            </div>
        `}_renderError(){return this._error?B`
            <div class="pluck-error">
                <ha-svg-icon .path=${"M11,15H13V17H11V15M11,7H13V13H11V7M12,2C6.47,2 2,6.5 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20Z"}></ha-svg-icon>
                <span>${this._error}</span>
            </div>
        `:""}_renderCommandState(){return B`
            <div class="field">
                <label>Command name</label>
                <input
                    type="text"
                    .value=${this._commandName}
                    placeholder="e.g. pwr_on"
                    autofocus
                    @input=${e=>this._commandName=e.target.value}
                    @keydown=${e=>{"Enter"===e.key&&this._pluck()}}
                />
                <div class="help">
                    The name you gave this code when you learned it in the
                    vendor app.
                </div>
            </div>
            ${this._renderError()}
            <div class="dialog-actions">
                <button
                    class="action-btn cancel-btn"
                    @click=${this._close}
                    ?disabled=${this._busy}
                >
                    Cancel
                </button>
                <button
                    class="action-btn pluck-btn"
                    @click=${this._pluck}
                    ?disabled=${this._busy}
                >
                    ${this._busy?"Plucking...":"Pluck"}
                </button>
            </div>
        `}_renderCaptures(e){const t=e.length>1;return B`
            ${this._renderError()}
            <div class="captured-label">
                Captured ${t?`(${e.length})`:""}
            </div>
            ${e.map((e,i)=>B`
                    <div class="capture">
                        ${t?B`<button
                                  class="remove-btn"
                                  title="Remove this capture"
                                  @click=${()=>this._removeCapture(i)}
                              >
                                  &times;
                              </button>`:""}
                        <div class="pronto">${e.code}</div>
                        ${this._renderValid(e,i)}
                        <div class="field">
                            <label>Alias</label>
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
                    Cancel
                </button>
                <button
                    class="action-btn create-btn"
                    @click=${this._create}
                    ?disabled=${this._creating}
                >
                    ${this._creating?"Saving...":"Create"}
                </button>
            </div>
        `}render(){return B`
            <ha-dialog
                open
                heading="Pluck Signal"
                scrimClickAction=""
                @closed=${this._close}
            >
                ${this._captures?this._renderCaptures(this._captures):this._renderCommandState()}
            </ha-dialog>
        `}};bs.styles=r`
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
        .help {
            font-size: 0.78rem;
            color: var(--secondary-text-color);
            margin-top: 4px;
        }
        input[type="text"] {
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
    `,e([he({attribute:!1})],bs.prototype,"api",void 0),e([he({attribute:!1})],bs.prototype,"blaster",void 0),e([he()],bs.prototype,"integration",void 0),e([pe()],bs.prototype,"_commandName",void 0),e([pe()],bs.prototype,"_busy",void 0),e([pe()],bs.prototype,"_creating",void 0),e([pe()],bs.prototype,"_error",void 0),e([pe()],bs.prototype,"_captures",void 0),e([pe()],bs.prototype,"_aliases",void 0),e([pe()],bs.prototype,"_validations",void 0),bs=e([ue("ir-pluck-signal-dialog")],bs);const fs="M0.861,24c-0.22,0-0.441-0.084-0.609-0.252c-0.336-0.336-0.336-0.882,0-1.218l1.563-1.563c1.648-1.649,3.474-4.166,5.588-7.082c2.984-4.116,6.367-8.781,10.695-13.109c0.081-0.081,0.178-0.145,0.284-0.189l1.283-0.523c0.441-0.18,0.943,0.032,1.123,0.472l-0.472,1.123L19.194,2.116c-4.175,4.199-7.478,8.755-10.397,12.78c-0.275,0.379-0.545,0.752-0.811,1.117c0.365-0.266,0.738-0.536,1.117-0.811C13.128,12.284,17.685,8.98,21.884,4.806l0.457-1.121L23.464,3.212c0.44,0.18,0.652,0.682,0.472,1.123l-0.523,1.283c-0.043,0.106-0.107,0.203-0.188,0.284c-4.329,4.329-8.994,7.711-13.109,10.695c-2.915,2.114-5.433,3.939-7.082,5.588l-1.563,1.563C1.302,23.916,1.082,24,0.861,24z",ys="M7,19V17H9V19H7M11,19V17H13V19H11M15,19V17H17V19H15M7,15V13H9V15H7M11,15V13H13V15H11M15,15V13H17V15H15M7,11V9H9V11H7M11,11V9H13V11H11M15,11V9H17V11H15M7,7V5H9V7H7M11,7V5H13V7H11M15,7V5H17V7H15Z";let xs=class extends ne{constructor(){super(...arguments),this.pendingEntity="",this._devices=[],this._hairDevices=[],this._triggers=[],this._loading=!0,this._error=null,this._expandedId=null,this._expandedDevice=null,this._confirmClearAll=!1,this._deleteRemoteId=null,this._deleteRemoteLabel="",this._deleteRemoteCount=0,this._vendorIntegration={},this._editingDeviceId=null,this._editLabel="",this._createRemoteOpen=!1,this._promoteTarget=null,this._pluckDialog=null,this._editSignal=null,this._assignSignal=null,this._deleteSignal=null,this._triggerDialog=null,this._triggerEditDialog=null,this._triggerPopover=null,this._assignedPopover=null,this._receivers=[],this._unsubUpdated=null,this._confirmDeleteTriggerId=null,this._testDialog=null,this._testEmitters=[],this._testingSignalId=null,this._testResult=null,this._remotesVersion=0,this._signalsVersion=0,this._remotesSortable=null,this._signalsSortable=null,this._signalsSortableContainer=null,this._pendingRemotesSave=null,this._pendingSignalsSave=null,this._onDocClickForPopover=e=>{const t=e.composedPath(),i=this.shadowRoot?.querySelector("ir-trigger-popover"),s=this.shadowRoot?.querySelector("ir-assigned-popover");i&&t.includes(i)||s&&t.includes(s)||(this._closeTriggerPopover(),this._closeAssignedPopover())},this._onScrollForPopover=()=>{this._closeTriggerPopover(),this._closeAssignedPopover()}}connectedCallback(){super.connectedCallback(),this._load(),this._subscribeUpdated()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribeUpdated(),this._removePopoverDismiss(),this._remotesSortable?.destroy(),this._remotesSortable=null,this._signalsSortable?.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null,null!==this._pendingRemotesSave&&clearTimeout(this._pendingRemotesSave),null!==this._pendingSignalsSave&&clearTimeout(this._pendingSignalsSave)}updated(e){if(super.updated(e),e.has("_editingDeviceId")&&this._editingDeviceId){const e=this.shadowRoot?.querySelector(".rename-input");e?.focus(),e?.select()}this._syncSortables()}_syncSortables(){const e=this.renderRoot.querySelector(".device-list");e&&!this._remotesSortable?this._attachRemotesSortable(e):!e&&this._remotesSortable&&(this._remotesSortable.destroy(),this._remotesSortable=null);const t=this.renderRoot.querySelector(".signal-list"),i=!!this._expandedDevice;!t||!i||this._signalsSortable&&this._signalsSortableContainer===t?t&&i||!this._signalsSortable||(this._signalsSortable.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null):(this._signalsSortable?.destroy(),this._attachSignalsSortable(t))}_attachRemotesSortable(e){this._remotesSortable=di.create(e,{handle:".remote-grip",animation:150,ghostClass:"sortable-ghost",onEnd:t=>{const{oldIndex:i,newIndex:s}=t;if(void 0===i||void 0===s||i===s)return;const o=[...this._devices],[a]=o.splice(i,1);o.splice(s,0,a),this._devices=o,this._remotesSortable?.destroy(),this._remotesSortable=null,this._purgeChildren(e,"ha-card"),this._remotesVersion++,this._scheduleRemotesSave(o.map(e=>e.id))}})}_attachSignalsSortable(e){this._expandedDevice&&(this._signalsSortableContainer=e,this._signalsSortable=di.create(e,{handle:".signal-grip",animation:150,ghostClass:"sortable-ghost",onEnd:t=>{const{oldIndex:i,newIndex:s}=t;if(void 0===i||void 0===s||i===s)return;const o=this._expandedDevice;if(!o)return;const a=[...o.signals],[r]=a.splice(i,1);a.splice(s,0,r),this._expandedDevice={...o,signals:a},this._signalsSortable?.destroy(),this._signalsSortable=null,this._signalsSortableContainer=null,this._purgeChildren(e,".signal-row"),this._signalsVersion++,this._scheduleSignalsSave(o.id,a.map(e=>e.id))}}))}_purgeChildren(e,t){for(const i of Array.from(e.querySelectorAll(t)))i.remove()}_scheduleRemotesSave(e){null!==this._pendingRemotesSave&&clearTimeout(this._pendingRemotesSave),this._pendingRemotesSave=window.setTimeout(async()=>{this._pendingRemotesSave=null;try{await this.api.reorderUnknownDevices("plucked",e)}catch(e){this._error=`Reorder failed: ${e.message}`,await this._load()}},500)}_scheduleSignalsSave(e,t){null!==this._pendingSignalsSave&&clearTimeout(this._pendingSignalsSave),this._pendingSignalsSave=window.setTimeout(async()=>{this._pendingSignalsSave=null;try{await this.api.reorderUnknownSignals(e,t)}catch(e){this._error=`Reorder failed: ${e.message}`,await this._refreshExpanded()}},500)}async _load(){this._loading=!0;try{const[e,t,i,s]=await Promise.all([this.api.getUnknownDevices({include_dismissed:!1,min_hits:0,source:"plucked"}),this.api.listDevices(),this.api.listTriggers(),this.api.listPluckVendors().catch(()=>({vendors:[]}))]);this._devices=e,this._hairDevices=t,this._triggers=i,this._vendorIntegration=this._mapIntegrations(s.vendors),this._error=null,this.api.listReceivers().then(e=>{this._receivers=e}).catch(()=>{this._receivers=[]})}catch(e){this._error=`Failed to load: ${e.message}`}finally{this._loading=!1}}_mapIntegrations(e){const t={};for(const i of e)for(const e of i.blasters)t[e.entity_id]=i.integration;return t}async _refreshExpanded(){if(this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{this._expandedId=null,this._expandedDevice=null}}openCreateRemote(){this._createRemoteOpen=!0}async _onBlasterCreated(e){this._createRemoteOpen=!1,this.pendingEntity="",await this._load(),this._expandedId=e.detail.id,await this._refreshExpanded()}_openPluckSignal(e,t){t.stopPropagation();const i=e.vendor_entity_id?this._vendorIntegration[e.vendor_entity_id]??"":"";i?this._pluckDialog={device:e,integration:i}:this._error="This blaster's integration is not available right now. Make sure the vendor integration is loaded."}async _onSignalsCreated(){this._pluckDialog=null,await this._refreshExpanded(),await this._load()}_openEditSignal(e,t,i){i.stopPropagation(),this._editSignal={deviceId:e,signal:t}}async _onSignalEdited(){this._editSignal=null,await this._refreshExpanded(),await this._load()}_openDeleteRemote(e){this._deleteRemoteId=e.id,this._deleteRemoteLabel=e.label||"this blaster",this._deleteRemoteCount=e.signals.length}async _confirmDeleteRemote(){const e=this._deleteRemoteId;if(this._deleteRemoteId=null,e)try{await this.api.deletePluckedBlaster(e),this._expandedId===e&&(this._expandedId=null,this._expandedDevice=null),await this._load()}catch(e){this._error=`Delete failed: ${e.message}`}}async _doClearAll(){this._confirmClearAll=!1;try{await this.api.clearUnknowns("plucked"),this._devices=[],this._expandedId=null,this._expandedDevice=null}catch(e){this._error=`Clear failed: ${e.message}`}}_onAliasChanged(e){const{id:t,alias:i}=e.detail;this._expandedDevice&&(this._expandedDevice={...this._expandedDevice,signals:this._expandedDevice.signals.map(e=>e.id===t?{...e,alias:i}:e)})}_startRename(e,t){t.stopPropagation(),this._editingDeviceId=e.id,this._editLabel=e.label??""}async _commitRename(e){const t=this._editLabel.trim();this._editingDeviceId=null;try{const i=await this.api.renameUnknown(e,t),s=this._devices.findIndex(t=>t.id===e);if(s>=0){const e=[...this._devices];e[s]={...e[s],label:i.label},this._devices=e}}catch(e){this._error=`Rename failed: ${e.message}`}}_onRenameKeydown(e,t){"Enter"===t.key?this._commitRename(e):"Escape"===t.key&&(this._editingDeviceId=null)}_openAssign(e,t,i){this._assignSignal={deviceId:e,signal:t,label:i??null}}_onAssignClick(e,t,i,s){if(!t.assigned_to?.length)return void this._openAssign(e,t,i);const o=s?.currentTarget,a=o?.getBoundingClientRect();this._assignedPopover={deviceId:e,signal:t,label:i??null,top:a?a.bottom+4:120,left:a?Math.max(8,a.right-220):120},this._installPopoverDismiss()}_closeAssignedPopover(){this._assignedPopover=null,this._removePopoverDismiss()}_onAssignedPopoverCreateNew(){const e=this._assignedPopover;this._closeAssignedPopover(),e&&this._openAssign(e.deviceId,e.signal,e.label)}_onAssignedPopoverOpen(e){const t=e.detail;this._closeAssignedPopover(),t&&this.dispatchEvent(new CustomEvent("navigate-device",{detail:t.device_id,bubbles:!0,composed:!0}))}async _onSignalAssigned(e){this._assignSignal=null,await this._load(),await this._refreshExpanded()}_matchesHairDevice(e){if(!e)return!1;const t=e.toLowerCase();return this._hairDevices.some(e=>e.name.toLowerCase()===t)}_promoteDevice(e,t){t.stopPropagation(),this._promoteTarget=e}async _onDevicePromoted(){this._promoteTarget=null,await this._load()}_openDelete(e,t){this._deleteSignal={deviceId:e,signal:t}}async _confirmDelete(){if(!this._deleteSignal)return;const{deviceId:e,signal:t}=this._deleteSignal;this._deleteSignal=null;try{await this.api.deleteSignal(e,t.id),await this._load(),await this._refreshExpanded()}catch(e){this._error=`Delete failed: ${e.message}`}}_openTestDialog(e){this._testDialog={signal:e}}async _sendTest(e){if(!this._testDialog)return;const{signal:t}=this._testDialog,i=e.detail.emitters;if(0!==i.length){this._testingSignalId=t.id,this._testResult=null,this._testDialog=null;try{const e=(await Promise.allSettled(i.map(e=>this.api.testSignal(t.id,e)))).filter(e=>"fulfilled"===e.status&&e.value.sent).length,s=i.length;this._testResult=e===s?1===s?"Sent!":`Sent! (${e}/${s})`:0===e?"Failed":`Sent (${e}/${s})`}catch{this._testResult="Error"}setTimeout(()=>{this._testResult=null,this._testingSignalId=null},3e3)}}_hasTrigger(e){return this._triggers.some(t=>rs(t,e))}_triggerCountFor(e){return this._triggers.filter(t=>rs(t,e)).length}_openTriggerDialog(e,t,i){const s=this._triggers.filter(e=>rs(e,t));if(0===s.length)return void(this._triggerDialog={signal:t,deviceId:e});const o=i?.currentTarget,a=o?.getBoundingClientRect();this._triggerPopover={deviceId:e,signal:t,top:a?a.bottom+4:120,left:a?Math.max(8,a.right-220):120},this._installPopoverDismiss()}_closeTriggerPopover(){this._triggerPopover=null,this._removePopoverDismiss()}_onPopoverCreateNew(){const e=this._triggerPopover;this._closeTriggerPopover(),e&&(this._triggerDialog={signal:e.signal,deviceId:e.deviceId})}_onPopoverEditTrigger(e){const t=e.detail;this._closeTriggerPopover(),t&&(this._triggerEditDialog=t)}_installPopoverDismiss(){setTimeout(()=>{document.addEventListener("click",this._onDocClickForPopover,!0),window.addEventListener("scroll",this._onScrollForPopover,!0)},0)}_removePopoverDismiss(){document.removeEventListener("click",this._onDocClickForPopover,!0),window.removeEventListener("scroll",this._onScrollForPopover,!0)}async _subscribeUpdated(){try{this._unsubUpdated=await this.api.subscribeSignalUpdated(()=>{this._refreshAfterSignalUpdate()})}catch{}}async _unsubscribeUpdated(){this._unsubUpdated&&(await this._unsubUpdated(),this._unsubUpdated=null)}async _refreshAfterSignalUpdate(){try{this._triggers=await this.api.listTriggers()}catch{}if(this._expandedId)try{this._expandedDevice=await this.api.getUnknownDevice(this._expandedId)}catch{}}_closeTriggerDialog(){this._triggerDialog=null,this._triggerEditDialog=null}_requestDeleteTrigger(e){this._confirmDeleteTriggerId=e}async _doDeleteTrigger(){if(!this._confirmDeleteTriggerId)return;const e=this._confirmDeleteTriggerId;this._confirmDeleteTriggerId=null,this._triggerEditDialog=null;try{await this.api.deleteTrigger(e),this._triggers=await this.api.listTriggers()}catch{}}async _onTriggerSaved(){this._triggerDialog=null,this._triggerEditDialog=null;try{this._triggers=await this.api.listTriggers()}catch{}}async _toggleExpand(e){if(this._expandedId===e)return this._expandedId=null,void(this._expandedDevice=null);this._expandedId=e,await this._refreshExpanded()}render(){const e=this._devices.length;return B`
            <div class="toolbar">
                <span class="title">
                    <ha-svg-icon .path=${fs}></ha-svg-icon>
                    HAIR Plucker
                    ${this._loading?"":B`<span class="count"
                              >(${e} ${1===e?"blaster":"blasters"})</span
                          >`}
                </span>
                <div class="toolbar-actions">
                    <button
                        class="create-btn"
                        @click=${()=>this._createRemoteOpen=!0}
                    >
                        + Add Blaster
                    </button>
                </div>
            </div>

            ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}

            ${this._loading?B`<div class="loading">Loading...</div>`:0===e?B`
                        <ha-card class="empty">
                            <ha-svg-icon class="empty-icon" .path=${fs}></ha-svg-icon>
                            <h3>No plucked blasters yet</h3>
                            <p>
                                The Plucker imports IR codes from your existing
                                blasters so you can use them in HAIR without
                                re-learning each one.
                            </p>
                            <p class="hint">
                                Click "+ Add Blaster" above to mirror a blaster.
                            </p>
                        </ha-card>
                    `:B`
                        <div class="device-list">
                            ${Se(this._remotesVersion,Te(this._devices,e=>e.id,e=>this._renderDevice(e)))}
                        </div>
                    `}

            ${e>0?B`
                      <div class="clear-all-row">
                          <button
                              class="action-btn delete-btn"
                              title="Delete all plucked blasters and their signals. Sniffed and clipped signals are untouched."
                              @click=${()=>this._confirmClearAll=!0}
                          >
                              Clear All
                          </button>
                      </div>
                  `:""}

            ${this._renderDialogs()}
        `}_renderDevice(e){const t=this._expandedId===e.id;return B`
            <ha-card class="device pluck-device">
                <div class="device-row" @click=${()=>this._toggleExpand(e.id)}>
                    <div class="device-info">
                        <div class="device-header">
                            ${this._editingDeviceId===e.id?B`<input
                                      class="rename-input"
                                      type="text"
                                      .value=${this._editLabel}
                                      @input=${e=>{this._editLabel=e.target.value}}
                                      @keydown=${t=>this._onRenameKeydown(e.id,t)}
                                      @blur=${()=>{this._commitRename(e.id)}}
                                      @click=${e=>e.stopPropagation()}
                                  />`:B`<ha-svg-icon
                                          class="remote-grip"
                                          .path=${ys}
                                          title="Drag to reorder"
                                          @click=${e=>e.stopPropagation()}
                                      ></ha-svg-icon>
                                      <span
                                          class="protocol"
                                          title="Click to rename"
                                          @click=${t=>this._startRename(e,t)}
                                          >${e.label??"Blaster"}</span
                                      >`}
                            ${e.appliance?B`<span
                                      class="appliance-badge"
                                      @click=${e=>e.stopPropagation()}
                                      >${e.appliance}</span
                                  >`:""}
                            <span class="stat"
                                ><strong>${e.signal_count}</strong>
                                ${1===e.signal_count?"signal":"signals"}</span
                            >
                            ${e.label&&this._matchesHairDevice(e.label)?B`<span
                                      class="status-badge hair-device"
                                      @click=${e=>e.stopPropagation()}
                                      >HAIR Device</span
                                  >`:e.label?B`<span
                                        class="status-badge promote-badge"
                                        title="Create a HAIR device from this blaster"
                                        @click=${t=>this._promoteDevice(e,t)}
                                        >Promote</span
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
        `}_renderExpanded(e){return B`
            <div class="expanded">
                <div class="signal-header">
                    <span>Signals (${e.signals.length})</span>
                    <button
                        class="create-btn create-signal-btn"
                        title="Pluck a code off this blaster"
                        @click=${t=>this._openPluckSignal(e,t)}
                    >
                        + Pluck Signal
                    </button>
                </div>
                ${0===e.signals.length?B`<div class="no-signals-row">
                          <span class="no-signals"
                              >No signals yet. Click "+ Pluck Signal" to pull a
                              code off this blaster.</span
                          >
                      </div>`:B`
                          <div class="signal-list">
                              ${Se(this._signalsVersion,Te(e.signals,e=>e.id,t=>this._renderSignal(e.id,t,e.label)))}
                          </div>
                      `}
                <div class="remote-footer">
                    <button
                        class="action-btn delete-btn"
                        title="Delete this blaster and all its signals"
                        @click=${t=>{t.stopPropagation(),this._openDeleteRemote(e)}}
                    >
                        Delete blaster
                    </button>
                </div>
            </div>
        `}_renderSignal(e,t,i){const s=this._testingSignalId===t.id;return B`
            <div class="signal-row">
                <ha-svg-icon
                    class="signal-grip"
                    .path=${ys}
                    title="Drag to reorder"
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
                    ${s&&this._testResult?B`<span class="test-result">${this._testResult}</span>`:B`<span>${Math.round(t.frequency/1e3)} kHz</span>`}
                </div>
                ${t.code?B`<button
                          title="View or edit code"
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
                        title=${t.assignment_count&&t.assigned_to?.length?1===t.assignment_count?`Assigned to ${t.assigned_to[0].device_name} / ${t.assigned_to[0].command_name}`:`Assigned to ${t.assignment_count} commands:\n- ${t.assigned_to.map(e=>`${e.device_name} / ${e.command_name}`).join("\n- ")}`:"Assign this signal to a HAIR device"}
                        @click=${s=>{s.stopPropagation(),this._onAssignClick(e,t,i,s)}}
                    >
                        Assign<ir-count-dot
                            color="green"
                            .count=${t.assignment_count??0}
                        ></ir-count-dot>
                    </button>
                    <button
                        class="action-btn test-btn"
                        ?disabled=${s}
                        title="Send this signal through an emitter"
                        @click=${e=>{e.stopPropagation(),this._openTestDialog(t)}}
                    >
                        ${s?"Sending...":"Test"}
                    </button>
                    <button
                        class="action-btn trigger-btn"
                        title=${this._hasTrigger(t)?"Edit trigger(s) for this signal":"Create an HA event entity that fires on this signal"}
                        @click=${i=>{i.stopPropagation(),this._openTriggerDialog(e,t,i)}}
                    >
                        Trigger<ir-count-dot
                            color="yellow"
                            .count=${this._triggerCountFor(t)}
                        ></ir-count-dot>
                    </button>
                    <button
                        class="action-btn delete-btn"
                        @click=${i=>{i.stopPropagation(),this._openDelete(e,t)}}
                    >
                        Delete
                    </button>
                </div>
            </div>
        `}_renderDialogs(){return B`
            ${this._createRemoteOpen?B`<ir-pluck-add-remote-dialog
                      .api=${this.api}
                      .pendingEntity=${this.pendingEntity}
                      @blaster-created=${this._onBlasterCreated}
                      @closed=${()=>{this._createRemoteOpen=!1,this.pendingEntity=""}}
                  ></ir-pluck-add-remote-dialog>`:""}

            ${this._promoteTarget?B`<ir-promote-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .suggestedName=${this._promoteTarget.label??""}
                      @device-created=${this._onDevicePromoted}
                      @closed=${()=>this._promoteTarget=null}
                  ></ir-promote-dialog>`:""}

            ${this._pluckDialog?B`<ir-pluck-signal-dialog
                      .api=${this.api}
                      .blaster=${this._pluckDialog.device}
                      .integration=${this._pluckDialog.integration}
                      @signals-created=${this._onSignalsCreated}
                      @closed=${()=>this._pluckDialog=null}
                  ></ir-pluck-signal-dialog>`:""}

            ${this._editSignal?B`<ir-signal-editor
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

            ${this._assignSignal?B`<ir-assign-signal-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .unknownDeviceId=${this._assignSignal.deviceId}
                      .signal=${this._assignSignal.signal}
                      .suggestedDeviceName=${this._assignSignal.label??""}
                      .initialMode=${"existing"}
                      @signal-assigned=${this._onSignalAssigned}
                      @closed=${()=>this._assignSignal=null}
                  ></ir-assign-signal-dialog>`:""}

            ${this._deleteSignal?B`<ir-confirm-dialog
                      title="Delete Signal"
                      message="Remove this signal permanently? This cannot be undone."
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._confirmDelete}
                      @closed=${()=>this._deleteSignal=null}
                  ></ir-confirm-dialog>`:""}

            ${this._confirmClearAll?B`<ir-confirm-dialog
                      title="Clear All Plucked"
                      message="Remove all plucked blasters and their signals? This cannot be undone. Sniffed and clipped signals are not affected."
                      confirmLabel="Clear All"
                      .destructive=${!0}
                      @confirmed=${this._doClearAll}
                      @closed=${()=>this._confirmClearAll=!1}
                  ></ir-confirm-dialog>`:""}

            ${this._deleteRemoteId?B`<ir-confirm-dialog
                      title="Delete Blaster"
                      message=${this._deleteRemoteCount>0?`Remove "${this._deleteRemoteLabel}" and its ${this._deleteRemoteCount} ${1===this._deleteRemoteCount?"signal":"signals"}? This cannot be undone.`:`Remove "${this._deleteRemoteLabel}"? This cannot be undone.`}
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._confirmDeleteRemote}
                      @closed=${()=>this._deleteRemoteId=null}
                  ></ir-confirm-dialog>`:""}

            ${this._triggerPopover?B`<ir-trigger-popover
                      .triggers=${this._triggers.filter(e=>rs(e,this._triggerPopover.signal))}
                      .receivers=${this._receivers}
                      .top=${this._triggerPopover.top}
                      .left=${this._triggerPopover.left}
                      @create-new=${this._onPopoverCreateNew}
                      @edit-trigger=${this._onPopoverEditTrigger}
                  ></ir-trigger-popover>`:""}

            ${this._assignedPopover?B`<ir-assigned-popover
                      .assignments=${this._assignedPopover.signal.assigned_to??[]}
                      .top=${this._assignedPopover.top}
                      .left=${this._assignedPopover.left}
                      @create-new=${this._onAssignedPopoverCreateNew}
                      @open-assignment=${this._onAssignedPopoverOpen}
                  ></ir-assigned-popover>`:""}

            ${this._triggerDialog?B`<ir-trigger-dialog
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

            ${this._triggerEditDialog?B`<ir-trigger-dialog
                      .api=${this.api}
                      .trigger=${this._triggerEditDialog}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                      @trigger-delete=${e=>this._requestDeleteTrigger(e.detail.triggerId)}
                  ></ir-trigger-dialog>`:""}

            ${this._confirmDeleteTriggerId?B`<ir-confirm-dialog
                      title="Delete Trigger"
                      message="Remove this trigger? The associated HA event entity will also be removed."
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._doDeleteTrigger}
                      @closed=${()=>this._confirmDeleteTriggerId=null}
                  ></ir-confirm-dialog>`:""}

            ${this._testDialog?B`<ir-test-emitter-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .value=${this._testEmitters}
                      @emitters-changed=${e=>this._testEmitters=e.detail.value}
                      @send=${this._sendTest}
                      @closed=${()=>this._testDialog=null}
                  ></ir-test-emitter-dialog>`:""}
        `}};function $s(e){if(!e)return"";try{const t=Date.now()-new Date(e).getTime();return t<6e4?"just now":t<36e5?`${Math.floor(t/6e4)}m`:t<864e5?`${Math.floor(t/36e5)}h`:`${Math.floor(t/864e5)}d`}catch{return""}}xs.styles=[Ei,r`
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
        .create-btn {
            background: none;
            color: #78909c;
            border: 1px solid #78909c;
            border-radius: 4px;
            padding: 4px 10px;
            font-size: 0.75rem;
            font-weight: 500;
            font-family: inherit;
            cursor: pointer;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            transition: background 150ms ease;
        }
        .create-btn:hover:not(:disabled) {
            background: rgba(120, 144, 156, 0.12);
        }
        .create-btn:disabled {
            opacity: 0.5;
            cursor: default;
        }
        /* Borderless text action, consistent with the Clipper's "+ Add
           Signal". Lighter slate to match the Add Blaster button. */
        .create-signal-btn {
            border: none;
            background: none;
            padding: 0;
            font-size: 0.64rem;
            position: relative;
            top: 1px;
            color: #78909c;
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
    `],e([he({attribute:!1})],xs.prototype,"api",void 0),e([he({attribute:!1})],xs.prototype,"hass",void 0),e([he()],xs.prototype,"pendingEntity",void 0),e([pe()],xs.prototype,"_devices",void 0),e([pe()],xs.prototype,"_hairDevices",void 0),e([pe()],xs.prototype,"_triggers",void 0),e([pe()],xs.prototype,"_loading",void 0),e([pe()],xs.prototype,"_error",void 0),e([pe()],xs.prototype,"_expandedId",void 0),e([pe()],xs.prototype,"_expandedDevice",void 0),e([pe()],xs.prototype,"_confirmClearAll",void 0),e([pe()],xs.prototype,"_deleteRemoteId",void 0),e([pe()],xs.prototype,"_deleteRemoteLabel",void 0),e([pe()],xs.prototype,"_deleteRemoteCount",void 0),e([pe()],xs.prototype,"_editingDeviceId",void 0),e([pe()],xs.prototype,"_editLabel",void 0),e([pe()],xs.prototype,"_createRemoteOpen",void 0),e([pe()],xs.prototype,"_promoteTarget",void 0),e([pe()],xs.prototype,"_pluckDialog",void 0),e([pe()],xs.prototype,"_editSignal",void 0),e([pe()],xs.prototype,"_assignSignal",void 0),e([pe()],xs.prototype,"_deleteSignal",void 0),e([pe()],xs.prototype,"_triggerDialog",void 0),e([pe()],xs.prototype,"_triggerEditDialog",void 0),e([pe()],xs.prototype,"_triggerPopover",void 0),e([pe()],xs.prototype,"_assignedPopover",void 0),e([pe()],xs.prototype,"_receivers",void 0),e([pe()],xs.prototype,"_confirmDeleteTriggerId",void 0),e([pe()],xs.prototype,"_testDialog",void 0),e([pe()],xs.prototype,"_testEmitters",void 0),e([pe()],xs.prototype,"_testingSignalId",void 0),e([pe()],xs.prototype,"_testResult",void 0),e([pe()],xs.prototype,"_remotesVersion",void 0),e([pe()],xs.prototype,"_signalsVersion",void 0),xs=e([ue("ir-pluck")],xs);let ws=class extends ne{constructor(){super(...arguments),this._device=null,this._loading=!0,this._error=null,this._triggers=[],this._receivers=[],this._hasReceivers=!0,this._filter="all",this._search="",this._bloomIds=new Set,this._assignSignal=null,this._assignedPopover=null,this._triggerDialog=null,this._triggerEditDialog=null,this._triggerPopover=null,this._confirmDeleteTriggerId=null,this._editSignal=null,this._testDialog=null,this._testEmitters=[],this._testingSignalId=null,this._testResult=null,this._unsubSignals=null,this._unsubUpdated=null,this._refreshTimer=null,this._onDocClickForPopover=e=>{const t=e.composedPath(),i=this.shadowRoot?.querySelector("ir-trigger-popover"),s=this.shadowRoot?.querySelector("ir-assigned-popover");i&&t.includes(i)||s&&t.includes(s)||(this._closeTriggerPopover(),this._closeAssignedPopover())},this._onScrollForPopover=()=>{this._closeTriggerPopover(),this._closeAssignedPopover()}}connectedCallback(){super.connectedCallback(),this._load(),this._subscribe()}disconnectedCallback(){super.disconnectedCallback(),this._unsubscribe(),this._removePopoverDismiss(),null!==this._refreshTimer&&(clearTimeout(this._refreshTimer),this._refreshTimer=null)}async _load(){this._loading=!0;try{const[e,t,i]=await Promise.all([this.api.getUnknownDevices({source:"echo",min_hits:0}),this.api.listTriggers(),this.api.getSnifferStatus()]);this._triggers=t,this._hasReceivers=i.has_receivers;const s=e.find(e=>e.fingerprint===as);this._device=s?await this.api.getUnknownDevice(s.id):null,this._error=null,this.api.listReceivers().then(e=>{this._receivers=e}).catch(()=>{this._receivers=[]})}catch(e){this._error=`Failed to load: ${e.message}`}finally{this._loading=!1}}async _refreshDevice(){if(this._device)try{this._device=await this.api.getUnknownDevice(this._device.id)}catch{await this._load()}else await this._load()}async _subscribe(){try{this._unsubSignals=await this.api.subscribeUnknownSignals(e=>this._onLiveSignal(e))}catch{}try{this._unsubUpdated=await this.api.subscribeSignalUpdated(()=>{this._refreshDots()})}catch{}}async _unsubscribe(){this._unsubSignals&&(await this._unsubSignals(),this._unsubSignals=null),this._unsubUpdated&&(await this._unsubUpdated(),this._unsubUpdated=null)}async _refreshDots(){try{this._triggers=await this.api.listTriggers()}catch{}await this._refreshDevice()}_onLiveSignal(e){e.device_fingerprint===as&&(this._bloomIds=new Set([...this._bloomIds,e.signal_id]),setTimeout(()=>{const t=new Set(this._bloomIds);t.delete(e.signal_id),this._bloomIds=t},1400),null!==this._refreshTimer&&clearTimeout(this._refreshTimer),this._refreshTimer=window.setTimeout(()=>{this._refreshTimer=null,this._refreshDevice()},300))}_friendlyReceiver(e){const t=this._receivers.find(t=>t.entity_id===e);if(t?.name)return t.name;const i=this.hass?.states?.[e];return i?.attributes?.friendly_name??e}_receiverArea(e){const t=this.hass?.entities?.[e],i=t?.area_id??(t?.device_id?this.hass?.devices?.[t.device_id]?.area_id:null);return i?this.hass?.areas?.[i]?.name??null:null}_decodedDisplay(e){const t=e.decoded_fingerprint;if(!t)return null;const i=t.split(":");return i.length>=3?`${i[0]} ${i[1]} : ${i.slice(2).join(":")}`:t}_rowView(e){const t=e.echo_source??"",i=t.indexOf(" -- via "),s=i>=0?t.slice(0,i):t,o=i>=0?t.slice(i+8):"",a=o?o.split(", "):[];let r,n=null;"automation send"===s||"integration send"===s?r=s:s.startsWith("Catalog test:")?(r="Catalog test",n=s.slice(13).trim()||null):s?(r="HAIR device",n=s):r="send";const l=e.alias||n||this._decodedDisplay(e)||"Unknown send",d=e.decoded_protocol??e.protocol,c=!e.decoded_protocol,h=a.length>2?`via ${a.length} emitters`:o?`via ${o}`:"";let p=null,g=!1;if(this._hasReceivers){const t=e.heard_by??[];if(0===t.length)p="not heard";else{g=!0;const e=t.map(e=>this._receiverArea(e));if(e.every(e=>null!==e))p=`heard in ${[...new Set(e)].join(", ")}`;else{const e=t.map(e=>this._friendlyReceiver(e));p=`heard by ${e.join(", ")}`}}}return{sig:e,title:l,pill:d??null,pillRaw:c,via:h,viaFull:o,emitters:a,chip:r,heard:p,heardOk:g}}_rows(){return(this._device?.signals??[]).map(e=>this._rowView(e))}_filteredRows(e){let t=e;"notheard"===this._filter?t=t.filter(e=>0===(e.sig.heard_by??[]).length):"all"!==this._filter&&(t=t.filter(e=>e.emitters.includes(this._filter)));const i=this._search.trim().toLowerCase();return i&&(t=t.filter(e=>[e.title,e.pill??"",e.viaFull,e.chip,e.sig.decoded_fingerprint??"",e.sig.alias??""].join(" ").toLowerCase().includes(i))),t}_triggerCountFor(e){return this._triggers.filter(t=>rs(t,e)).length}_onAssignClick(e,t){if(!this._device)return;if(!e.assigned_to?.length)return void(this._assignSignal={signal:e,initialMode:"existing"});const i=t?.currentTarget,s=i?.getBoundingClientRect();this._assignedPopover={signal:e,top:s?s.bottom+4:120,left:s?Math.max(8,s.right-220):120},this._installPopoverDismiss()}_closeAssignedPopover(){this._assignedPopover=null,this._removePopoverDismiss()}_onAssignedPopoverCreateNew(){const e=this._assignedPopover;this._closeAssignedPopover(),e&&(this._assignSignal={signal:e.signal,initialMode:"existing"})}_onAssignedPopoverOpen(e){const t=e.detail;this._closeAssignedPopover(),t&&this.dispatchEvent(new CustomEvent("navigate-device",{detail:t.device_id,bubbles:!0,composed:!0}))}async _onSignalAssigned(e){this._assignSignal=null,await this._refreshDots()}_openTriggerDialog(e,t){const i=this._triggers.filter(t=>rs(t,e));if(0===i.length)return void(this._triggerDialog=e);const s=t?.currentTarget,o=s?.getBoundingClientRect();this._triggerPopover={signal:e,top:o?o.bottom+4:120,left:o?Math.max(8,o.right-220):120},this._installPopoverDismiss()}_closeTriggerPopover(){this._triggerPopover=null,this._removePopoverDismiss()}_onPopoverCreateNew(){const e=this._triggerPopover;this._closeTriggerPopover(),e&&(this._triggerDialog=e.signal)}_onPopoverEditTrigger(e){const t=e.detail;this._closeTriggerPopover(),t&&(this._triggerEditDialog=t)}async _onTriggerSaved(){this._triggerDialog=null,this._triggerEditDialog=null;try{this._triggers=await this.api.listTriggers()}catch{}}_closeTriggerDialog(){this._triggerDialog=null,this._triggerEditDialog=null}_requestDeleteTrigger(e){this._closeTriggerDialog(),this._confirmDeleteTriggerId=e}async _confirmDeleteTrigger(){const e=this._confirmDeleteTriggerId;if(this._confirmDeleteTriggerId=null,e)try{await this.api.deleteTrigger(e),this._triggers=await this.api.listTriggers()}catch(e){this._error=`Delete failed: ${e.message}`}}_installPopoverDismiss(){setTimeout(()=>{document.addEventListener("click",this._onDocClickForPopover,!0),window.addEventListener("scroll",this._onScrollForPopover,!0)},0)}_removePopoverDismiss(){document.removeEventListener("click",this._onDocClickForPopover,!0),window.removeEventListener("scroll",this._onScrollForPopover,!0)}async _sendTest(e){if(!this._testDialog)return;const t=this._testDialog,i=e.detail.emitters;if(0!==i.length){this._testingSignalId=t.id,this._testResult=null,this._testDialog=null;try{const e=(await Promise.allSettled(i.map(e=>this.api.testSignal(t.id,e)))).filter(e=>"fulfilled"===e.status&&e.value.sent).length,s=i.length;this._testResult=e===s?1===s?"Sent!":`Sent! (${e}/${s})`:0===e?"Failed":`Sent (${e}/${s})`}catch{this._testResult="Error"}setTimeout(()=>{this._testResult=null,this._testingSignalId=null},3e3)}}async _onSignalEdited(){this._editSignal=null,await this._refreshDevice()}render(){const e=this._rows(),t=this._filteredRows(e);return B`
            ${this._error?B`<div class="error">${this._error}</div>`:""}
            ${this._loading&&!this._device?B`<div class="loading">Loading…</div>`:0===e.length?this._renderEmpty():B`
                        ${this._renderStats(e)}
                        ${this._renderToolbar(e)}
                        <div class="rows">
                            ${0===t.length?B`<div class="no-match">
                                      No sends match.
                                  </div>`:t.map(e=>this._renderRow(e))}
                        </div>
                    `}
            ${this._renderDialogs()}
        `}_renderStats(e){const t=e.filter(e=>0===(e.sig.heard_by??[]).length).length,i=new Set;for(const t of e)t.emitters.forEach(e=>i.add(e));const s=this._device?.last_seen;return B`
            <div class="stats">
                <div class="stat">
                    <div class="v">${this._device?.hit_count??0}</div>
                    <div class="l">SENDS</div>
                </div>
                ${this._hasReceivers?B`
                          <div class="stat">
                              <div class="v ${t?"warn":""}">
                                  ${t}
                              </div>
                              <div class="l">NOT HEARD</div>
                          </div>
                      `:""}
                <div class="stat">
                    <div class="v">${i.size}</div>
                    <div class="l">EMITTERS</div>
                </div>
                <div class="stat">
                    <div class="v">${e.length}</div>
                    <div class="l">SIGNALS</div>
                </div>
                <span class="updated">
                    ${this._hasReceivers?s?`last send ${$s(s)}${"just now"===$s(s)?"":" ago"}`:"":"no receivers"}
                </span>
            </div>
        `}_renderToolbar(e){const t=e.filter(e=>0===(e.sig.heard_by??[]).length).length,i=new Map;for(const t of e)for(const e of t.emitters)i.set(e,(i.get(e)??0)+1);return B`
            <div class="toolbar">
                <button
                    class="fchip ${"all"===this._filter?"on":""}"
                    @click=${()=>this._filter="all"}
                >
                    All (${e.length})
                </button>
                ${this._hasReceivers?B`
                          <button
                              class="fchip warnc ${"notheard"===this._filter?"on":""}"
                              @click=${()=>this._filter="notheard"}
                          >
                              Not heard (${t})
                          </button>
                      `:""}
                ${[...i.entries()].map(([e,t])=>B`
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
                    placeholder="Search sends..."
                    .value=${this._search}
                    @input=${e=>{this._search=e.target.value}}
                />
            </div>
        `}_renderRow(e){const t=e.sig,i=this._bloomIds.has(t.id),s=!!t.code,o=this._testingSignalId===t.id;return B`
            <div class="mrow ${i?"bloom":""}">
                <div class="mrow-main">
                    <div class="mrow-title">
                        <span class="name">${e.title}</span>
                        ${e.pill?B`<span
                                  class="pill ${e.pillRaw?"raw":""}"
                                  >${e.pill}</span
                              >`:""}
                    </div>
                    <div class="mrow-sub">
                        ${e.via?B`<span title=${e.viaFull}>${e.via}</span>`:""}
                        ${null!==e.heard?B`
                                  <span class="arrow">&#10142;</span>
                                  <span
                                      class=${e.heardOk?"heard":"not-heard"}
                                      >${e.heard}</span
                                  >
                              `:""}
                        <span class="src-chip">${e.chip}</span>
                    </div>
                </div>
                <div class="mrow-meta">
                    <span class="counts"
                        >${t.hit_count}
                        ${1===t.hit_count?"send":"sends"}${t.last_seen?B` &middot; ${$s(t.last_seen)}`:""}</span
                    >
                    ${t.code?B`
                              <button
                                  class="code-btn"
                                  title="View or edit code"
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
                        title=${s?t.assignment_count&&t.assigned_to?.length?1===t.assignment_count?`Assigned to ${t.assigned_to[0].device_name} / ${t.assigned_to[0].command_name}`:`Assigned to ${t.assignment_count} commands:\n- ${t.assigned_to.map(e=>`${e.device_name} / ${e.command_name}`).join("\n- ")}`:"Assign this signal to a HAIR device":"Identity unknown -- nothing was heard back to assign"}
                        @click=${e=>{e.stopPropagation(),this._onAssignClick(t,e)}}
                    >Assign<ir-count-dot
                            color="green"
                            .count=${t.assignment_count??0}
                        ></ir-count-dot></button>
                    <button
                        class="action-btn test-btn"
                        ?disabled=${!s||o}
                        title=${s?"Send this signal through an emitter to test it":"Identity unknown -- nothing to send"}
                        @click=${e=>{e.stopPropagation(),this._testDialog=t}}
                    >${o?this._testResult??"Sending...":"Test"}</button>
                    <button
                        class="action-btn trigger-btn"
                        ?disabled=${!s}
                        title=${s?this._triggerCountFor(t)>0?"Edit trigger(s) for this signal":"Fires when this signal arrives from outside Home Assistant":"Identity unknown -- nothing to bind"}
                        @click=${e=>{e.stopPropagation(),this._openTriggerDialog(t,e)}}
                    >Trigger<ir-count-dot
                            color="yellow"
                            .count=${this._triggerCountFor(t)}
                        ></ir-count-dot></button>
                </div>
            </div>
        `}_renderEmpty(){return B`
            <div class="empty">
                <div class="mirror-glyph"></div>
                <div class="empty-title">Nothing sent yet</div>
                <div class="empty-sub">
                    Commands sent by HAIR devices, automations, or any
                    integration on the infrared platform will appear here,
                    with where they went and who heard them.
                </div>
            </div>
        `}_renderDialogs(){return B`
            ${this._triggerPopover?B`<ir-trigger-popover
                      .triggers=${this._triggers.filter(e=>rs(e,this._triggerPopover.signal))}
                      .receivers=${this._receivers}
                      .top=${this._triggerPopover.top}
                      .left=${this._triggerPopover.left}
                      @create-new=${this._onPopoverCreateNew}
                      @edit-trigger=${this._onPopoverEditTrigger}
                  ></ir-trigger-popover>`:""}
            ${this._assignedPopover?B`<ir-assigned-popover
                      .assignments=${this._assignedPopover.signal.assigned_to??[]}
                      .top=${this._assignedPopover.top}
                      .left=${this._assignedPopover.left}
                      @create-new=${this._onAssignedPopoverCreateNew}
                      @open-assignment=${this._onAssignedPopoverOpen}
                  ></ir-assigned-popover>`:""}
            ${this._triggerDialog?B`<ir-trigger-dialog
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
            ${this._triggerEditDialog?B`<ir-trigger-dialog
                      .api=${this.api}
                      .trigger=${this._triggerEditDialog}
                      .mirrorContext=${!0}
                      @trigger-saved=${this._onTriggerSaved}
                      @closed=${this._closeTriggerDialog}
                      @trigger-delete=${e=>this._requestDeleteTrigger(e.detail.triggerId)}
                  ></ir-trigger-dialog>`:""}
            ${this._confirmDeleteTriggerId?B`<ir-confirm-dialog
                      title="Delete Trigger"
                      message="Remove this trigger permanently? Automations using it will stop firing."
                      confirmLabel="Delete"
                      .destructive=${!0}
                      @confirmed=${this._confirmDeleteTrigger}
                      @closed=${()=>this._confirmDeleteTriggerId=null}
                  ></ir-confirm-dialog>`:""}
            ${this._assignSignal&&this._device?B`<ir-assign-signal-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .unknownDeviceId=${this._device.id}
                      .signal=${this._assignSignal.signal}
                      .suggestedDeviceName=${""}
                      .initialMode=${this._assignSignal.initialMode}
                      @signal-assigned=${this._onSignalAssigned}
                      @closed=${()=>this._assignSignal=null}
                  ></ir-assign-signal-dialog>`:""}
            ${this._editSignal&&this._device?B`<ir-signal-editor
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
            ${this._testDialog?B`<ir-test-emitter-dialog
                      .api=${this.api}
                      .hass=${this.hass}
                      .value=${this._testEmitters}
                      @emitters-changed=${e=>this._testEmitters=e.detail.value}
                      @send=${this._sendTest}
                      @closed=${()=>this._testDialog=null}
                  ></ir-test-emitter-dialog>`:""}
        `}};ws.styles=[Ei,r`
            :host {
                display: block;
            }
            .loading,
            .no-match {
                text-align: center;
                color: var(--secondary-text-color);
                padding: 24px;
            }
            .error {
                color: var(--error-color, #db4437);
                padding: 8px 0;
            }

            /* Stats strip: the silver sheen lives here, as texture. */
            .stats {
                display: flex;
                align-items: center;
                gap: 26px;
                background: var(--secondary-background-color);
                border: 1px solid var(--divider-color);
                border-radius: 10px;
                padding: 12px 18px;
                margin-bottom: 14px;
                background-image: linear-gradient(
                    105deg,
                    transparent 42%,
                    rgba(144, 164, 174, 0.12) 50%,
                    transparent 58%
                );
            }
            .stat .v {
                font-size: 19px;
                font-weight: 600;
                color: var(--primary-text-color);
            }
            .stat .l {
                font-size: 11px;
                color: var(--secondary-text-color);
                letter-spacing: 0.4px;
                margin-top: 1px;
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

            /* Rows */
            .rows {
                border: 1px solid var(--divider-color);
                border-radius: 10px;
                overflow: hidden;
            }
            .mrow {
                display: flex;
                align-items: center;
                gap: 12px;
                padding: 10px 16px;
                border-bottom: 1px solid var(--divider-color);
                background: var(--card-background-color);
            }
            .mrow:last-child {
                border-bottom: none;
            }
            .mrow:hover {
                background: var(--secondary-background-color);
            }
            /* The silver bloom a send makes while you watch. */
            .mrow.bloom {
                animation: mirror-bloom 1.4s ease-out;
            }
            @keyframes mirror-bloom {
                0% {
                    box-shadow:
                        inset 3px 0 0 #90a4ae,
                        0 0 10px rgba(144, 164, 174, 0.55);
                }
                100% {
                    box-shadow:
                        inset 3px 0 0 rgba(144, 164, 174, 0),
                        0 0 0 rgba(144, 164, 174, 0);
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
            .mrow-sub {
                margin-top: 4px;
                font-size: 12px;
                color: var(--secondary-text-color);
                display: flex;
                align-items: center;
                gap: 6px;
                flex-wrap: wrap;
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
            .mirror-glyph {
                width: 44px;
                height: 44px;
                margin: 0 auto 14px;
                border-radius: 10px;
                border: 2.5px solid #607d8b;
                background: linear-gradient(
                    135deg,
                    #eceff1 30%,
                    #ffffff 45%,
                    #eceff1 60%
                );
                position: relative;
            }
            .mirror-glyph::after {
                content: "";
                position: absolute;
                top: 5px;
                left: 11px;
                width: 5px;
                height: 24px;
                background: rgba(255, 255, 255, 0.95);
                transform: rotate(18deg);
                border-radius: 3px;
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
        `],e([he({attribute:!1})],ws.prototype,"api",void 0),e([he({attribute:!1})],ws.prototype,"hass",void 0),e([pe()],ws.prototype,"_device",void 0),e([pe()],ws.prototype,"_loading",void 0),e([pe()],ws.prototype,"_error",void 0),e([pe()],ws.prototype,"_triggers",void 0),e([pe()],ws.prototype,"_receivers",void 0),e([pe()],ws.prototype,"_hasReceivers",void 0),e([pe()],ws.prototype,"_filter",void 0),e([pe()],ws.prototype,"_search",void 0),e([pe()],ws.prototype,"_bloomIds",void 0),e([pe()],ws.prototype,"_assignSignal",void 0),e([pe()],ws.prototype,"_assignedPopover",void 0),e([pe()],ws.prototype,"_triggerDialog",void 0),e([pe()],ws.prototype,"_triggerEditDialog",void 0),e([pe()],ws.prototype,"_triggerPopover",void 0),e([pe()],ws.prototype,"_confirmDeleteTriggerId",void 0),e([pe()],ws.prototype,"_editSignal",void 0),e([pe()],ws.prototype,"_testDialog",void 0),e([pe()],ws.prototype,"_testEmitters",void 0),e([pe()],ws.prototype,"_testingSignalId",void 0),e([pe()],ws.prototype,"_testResult",void 0),ws=e([ue("ir-mirror")],ws);let ks=class extends ne{constructor(){super(...arguments),this.narrow=!1,this._activeTab="devices",this._devices=[],this._expandedDeviceId=null,this._loading=!0,this._error=null,this._addDialogOpen=!1,this._pluckersAvailable=!1,this._pendingPluckEntity="",this._api=null}connectedCallback(){super.connectedCallback(),this.hass&&this._init()}updated(e){e.has("hass")&&this.hass&&!this._api&&this._init()}_init(){this._api=new me(this.hass),this._refreshDevices(),this._checkPluckers()}async _checkPluckers(){if(this._api){try{const{vendors:e}=await this._api.listPluckVendors();this._pluckersAvailable=e.length>0}catch{this._pluckersAvailable=!1}"plucker"!==this._activeTab||this._pluckersAvailable||this._switchTab("devices")}}_tagline(){return{devices:"Manage your IR devices and the hardware that drives them.",sniffer:"Capture IR codes live from the air.",clips:"Build remotes by pasting known IR codes.",plucker:"Pluck IR codes from existing blasters.",mirror:"See what your house transmits."}[this._activeTab]}async _refreshDevices(){if(this._api){this._loading=!0;try{this._devices=await this._api.listDevices(),this._error=null}catch(e){this._error=`Failed to load devices: ${e.message}`}finally{this._loading=!1}}}_toggleDevice(e){this._expandedDeviceId=this._expandedDeviceId===e?null:e}_openAddDialog(){this._addDialogOpen=!0}_onNavigatePlucker(e){this._pendingPluckEntity=e.detail?.vendor_entity_id??"",this._switchTab("plucker")}_onNavigateDevice(e){this._switchTab("devices"),this._expandedDeviceId=e.detail}_closeAddDialog(){this._addDialogOpen=!1}async _onDeviceCreated(e){this._addDialogOpen=!1,await this._refreshDevices(),this._expandedDeviceId=e.detail.id}async _onDeviceChanged(){await this._refreshDevices()}async _onDeviceDeleted(){this._expandedDeviceId=null,await this._refreshDevices()}_switchTab(e){this._expandedDeviceId=null,this._activeTab=e,"devices"===e&&this._refreshDevices()}_openHaSidebar(){this.dispatchEvent(new Event("hass-toggle-menu",{bubbles:!0,composed:!0}))}render(){return this._api?B`
            <ha-top-app-bar-fixed>
                <ha-menu-button
                    slot="navigationIcon"
                    .hass=${this.hass}
                ></ha-menu-button>

            <div class="mobile-nav-row">
                <button
                    class="mobile-nav-button"
                    title="Open menu"
                    aria-label="Open menu"
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
                    Devices
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
                ${this._pluckersAvailable?B`<button
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
                ${this._error?B`<ha-alert alert-type="error">${this._error}</ha-alert>`:""}
                ${"devices"===this._activeTab?B`
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
                              @navigate-plucker=${this._onNavigatePlucker}
                              @add-device=${this._openAddDialog}
                          ></ir-device-list>

                      `:"sniffer"===this._activeTab?B`
                            <ir-signal-monitor
                                .api=${this._api}
                                .hass=${this.hass}
                                @navigate-device=${this._onNavigateDevice}
                            ></ir-signal-monitor>
                        `:"clips"===this._activeTab?B`
                              <ir-clips
                                  .api=${this._api}
                                  .hass=${this.hass}
                                  @navigate-device=${this._onNavigateDevice}
                              ></ir-clips>
                          `:"plucker"===this._activeTab?B`
                                <ir-pluck
                                    .api=${this._api}
                                    .hass=${this.hass}
                                    .pendingEntity=${this._pendingPluckEntity}
                                    @navigate-device=${this._onNavigateDevice}
                                ></ir-pluck>
                            `:B`
                                <ir-mirror
                                    .api=${this._api}
                                    .hass=${this.hass}
                                    @navigate-device=${this._onNavigateDevice}
                                ></ir-mirror>
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

            <div class="version-footer">v${"0.6.3"}</div>
            </ha-top-app-bar-fixed>
        `:B`<div class="loading">Loading…</div>`}};ks.styles=r`
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
        /* The Mirror wears silver (v0.6.3), matching its tab accent. */
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
    `,e([he({attribute:!1})],ks.prototype,"hass",void 0),e([he({attribute:!1})],ks.prototype,"narrow",void 0),e([he({attribute:!1})],ks.prototype,"route",void 0),e([he({attribute:!1})],ks.prototype,"panel",void 0),e([pe()],ks.prototype,"_activeTab",void 0),e([pe()],ks.prototype,"_devices",void 0),e([pe()],ks.prototype,"_expandedDeviceId",void 0),e([pe()],ks.prototype,"_loading",void 0),e([pe()],ks.prototype,"_error",void 0),e([pe()],ks.prototype,"_addDialogOpen",void 0),e([pe()],ks.prototype,"_pluckersAvailable",void 0),e([pe()],ks.prototype,"_pendingPluckEntity",void 0),ks=e([ue("ha-panel-ir-devices")],ks);export{ks as HaPanelIrDevices};
