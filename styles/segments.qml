<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis simplifyDrawingTol="1" simplifyLocal="1" readOnly="0" simplifyMaxScale="1" version="3.6.3-Noosa" simplifyAlgorithm="0" maxScale="0" minScale="1e+08" labelsEnabled="0" hasScaleBasedVisibilityFlag="0" styleCategories="AllStyleCategories" simplifyDrawingHints="1">
  <flags>
    <Identifiable>1</Identifiable>
    <Removable>1</Removable>
    <Searchable>1</Searchable>
  </flags>
  <renderer-v2 forceraster="0" enableorderby="0" symbollevels="0" type="singleSymbol">
    <symbols>
      <symbol force_rhr="0" alpha="1" clip_to_extent="1" name="0" type="line">
        <layer enabled="1" pass="0" locked="0" class="SimpleLine">
          <prop v="square" k="capstyle"/>
          <prop v="5;2" k="customdash"/>
          <prop v="3x:0,0,0,0,0,0" k="customdash_map_unit_scale"/>
          <prop v="MM" k="customdash_unit"/>
          <prop v="0" k="draw_inside_polygon"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="0,255,0,255" k="line_color"/>
          <prop v="solid" k="line_style"/>
          <prop v="1" k="line_width"/>
          <prop v="MM" k="line_width_unit"/>
          <prop v="0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="0" k="ring_filter"/>
          <prop v="0" k="use_custom_dash"/>
          <prop v="3x:0,0,0,0,0,0" k="width_map_unit_scale"/>
          <data_defined_properties>
            <Option type="Map">
              <Option name="name" type="QString" value=""/>
              <Option name="properties" type="Map">
                <Option name="outlineWidth" type="Map">
                  <Option name="active" type="bool" value="true"/>
                  <Option name="expression" type="QString" value="&quot;boundary&quot; * -1"/>
                  <Option name="type" type="int" value="3"/>
                </Option>
              </Option>
              <Option name="type" type="QString" value="collection"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
    <rotation/>
    <sizescale/>
  </renderer-v2>
  <customproperties>
    <property value="0" key="embeddedWidgets/count"/>
    <property key="variableNames"/>
    <property key="variableValues"/>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <SingleCategoryDiagramRenderer diagramType="Histogram" attributeLegend="1">
    <DiagramCategory backgroundAlpha="255" enabled="0" labelPlacementMethod="XHeight" scaleDependency="Area" penAlpha="255" lineSizeScale="3x:0,0,0,0,0,0" scaleBasedVisibility="0" barWidth="5" minimumSize="0" sizeScale="3x:0,0,0,0,0,0" opacity="1" sizeType="MM" backgroundColor="#ffffff" maxScaleDenominator="1e+08" penWidth="0" width="15" minScaleDenominator="0" diagramOrientation="Up" lineSizeType="MM" rotationOffset="270" height="15" penColor="#000000">
      <fontProperties style="" description="MS Shell Dlg 2,7.8,-1,5,50,0,0,0,0,0"/>
      <attribute field="" label="" color="#000000"/>
    </DiagramCategory>
  </SingleCategoryDiagramRenderer>
  <DiagramLayerSettings priority="0" dist="0" linePlacementFlags="18" obstacle="0" placement="2" zIndex="0" showAll="1">
    <properties>
      <Option type="Map">
        <Option name="name" type="QString" value=""/>
        <Option name="properties"/>
        <Option name="type" type="QString" value="collection"/>
      </Option>
    </properties>
  </DiagramLayerSettings>
  <geometryOptions geometryPrecision="0" removeDuplicateNodes="0">
    <activeChecks/>
    <checkConfiguration/>
  </geometryOptions>
  <fieldConfiguration>
    <field name="ID">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="boundary">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="vertices">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="length">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="azimuth">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="sinuosity">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="red_grad">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="green_grad">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="blue_grad">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="dsm_grad">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="cad_sum">
      <editWidget type="">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="cad_count">
      <editWidget type="">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="bound_ref">
      <editWidget type="">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias field="ID" index="0" name=""/>
    <alias field="boundary" index="1" name=""/>
    <alias field="vertices" index="2" name=""/>
    <alias field="length" index="3" name=""/>
    <alias field="azimuth" index="4" name=""/>
    <alias field="sinuosity" index="5" name=""/>
    <alias field="red_grad" index="6" name=""/>
    <alias field="green_grad" index="7" name=""/>
    <alias field="blue_grad" index="8" name=""/>
    <alias field="dsm_grad" index="9" name=""/>
    <alias field="cad_sum" index="10" name=""/>
    <alias field="cad_count" index="11" name=""/>
    <alias field="bound_ref" index="12" name=""/>
  </aliases>
  <excludeAttributesWMS/>
  <excludeAttributesWFS/>
  <defaults>
    <default field="ID" applyOnUpdate="0" expression=""/>
    <default field="boundary" applyOnUpdate="0" expression=""/>
    <default field="vertices" applyOnUpdate="0" expression=""/>
    <default field="length" applyOnUpdate="0" expression=""/>
    <default field="azimuth" applyOnUpdate="0" expression=""/>
    <default field="sinuosity" applyOnUpdate="0" expression=""/>
    <default field="red_grad" applyOnUpdate="0" expression=""/>
    <default field="green_grad" applyOnUpdate="0" expression=""/>
    <default field="blue_grad" applyOnUpdate="0" expression=""/>
    <default field="dsm_grad" applyOnUpdate="0" expression=""/>
    <default field="cad_sum" applyOnUpdate="0" expression=""/>
    <default field="cad_count" applyOnUpdate="0" expression=""/>
    <default field="bound_ref" applyOnUpdate="0" expression=""/>
  </defaults>
  <constraints>
    <constraint notnull_strength="0" field="ID" exp_strength="0" constraints="0" unique_strength="0"/>
    <constraint notnull_strength="0" field="boundary" exp_strength="0" constraints="0" unique_strength="0"/>
    <constraint notnull_strength="0" field="vertices" exp_strength="0" constraints="0" unique_strength="0"/>
    <constraint notnull_strength="0" field="length" exp_strength="0" constraints="0" unique_strength="0"/>
    <constraint notnull_strength="0" field="azimuth" exp_strength="0" constraints="0" unique_strength="0"/>
    <constraint notnull_strength="0" field="sinuosity" exp_strength="0" constraints="0" unique_strength="0"/>
    <constraint notnull_strength="0" field="red_grad" exp_strength="0" constraints="0" unique_strength="0"/>
    <constraint notnull_strength="0" field="green_grad" exp_strength="0" constraints="0" unique_strength="0"/>
    <constraint notnull_strength="0" field="blue_grad" exp_strength="0" constraints="0" unique_strength="0"/>
    <constraint notnull_strength="0" field="dsm_grad" exp_strength="0" constraints="0" unique_strength="0"/>
    <constraint notnull_strength="0" field="cad_sum" exp_strength="0" constraints="0" unique_strength="0"/>
    <constraint notnull_strength="0" field="cad_count" exp_strength="0" constraints="0" unique_strength="0"/>
    <constraint notnull_strength="0" field="bound_ref" exp_strength="0" constraints="0" unique_strength="0"/>
  </constraints>
  <constraintExpressions>
    <constraint field="ID" desc="" exp=""/>
    <constraint field="boundary" desc="" exp=""/>
    <constraint field="vertices" desc="" exp=""/>
    <constraint field="length" desc="" exp=""/>
    <constraint field="azimuth" desc="" exp=""/>
    <constraint field="sinuosity" desc="" exp=""/>
    <constraint field="red_grad" desc="" exp=""/>
    <constraint field="green_grad" desc="" exp=""/>
    <constraint field="blue_grad" desc="" exp=""/>
    <constraint field="dsm_grad" desc="" exp=""/>
    <constraint field="cad_sum" desc="" exp=""/>
    <constraint field="cad_count" desc="" exp=""/>
    <constraint field="bound_ref" desc="" exp=""/>
  </constraintExpressions>
  <expressionfields/>
  <attributeactions>
    <defaultAction value="{00000000-0000-0000-0000-000000000000}" key="Canvas"/>
  </attributeactions>
  <attributetableconfig sortExpression="" actionWidgetStyle="dropDown" sortOrder="0">
    <columns>
      <column hidden="0" width="-1" name="ID" type="field"/>
      <column hidden="0" width="-1" name="boundary" type="field"/>
      <column hidden="0" width="-1" name="vertices" type="field"/>
      <column hidden="0" width="-1" name="length" type="field"/>
      <column hidden="0" width="-1" name="azimuth" type="field"/>
      <column hidden="0" width="-1" name="sinuosity" type="field"/>
      <column hidden="0" width="-1" name="red_grad" type="field"/>
      <column hidden="0" width="-1" name="green_grad" type="field"/>
      <column hidden="0" width="-1" name="blue_grad" type="field"/>
      <column hidden="0" width="-1" name="dsm_grad" type="field"/>
      <column hidden="1" width="-1" type="actions"/>
    </columns>
  </attributetableconfig>
  <conditionalstyles>
    <rowstyles/>
    <fieldstyles/>
  </conditionalstyles>
  <editform tolerant="1"></editform>
  <editforminit/>
  <editforminitcodesource>0</editforminitcodesource>
  <editforminitfilepath></editforminitfilepath>
  <editforminitcode><![CDATA[# -*- coding: utf-8 -*-
"""
QGIS forms can have a Python function that is called when the form is
opened.

Use this function to add extra logic to your forms.

Enter the name of the function in the "Python Init function"
field.
An example follows:
"""
from qgis.PyQt.QtWidgets import QWidget

def my_form_open(dialog, layer, feature):
	geom = feature.geometry()
	control = dialog.findChild(QWidget, "MyLineEdit")
]]></editforminitcode>
  <featformsuppress>0</featformsuppress>
  <editorlayout>generatedlayout</editorlayout>
  <editable>
    <field editable="1" name="ID"/>
    <field editable="1" name="azimuth"/>
    <field editable="1" name="blue_grad"/>
    <field editable="1" name="boundary"/>
    <field editable="1" name="dsm_grad"/>
    <field editable="1" name="green_grad"/>
    <field editable="1" name="length"/>
    <field editable="1" name="red_grad"/>
    <field editable="1" name="sinuosity"/>
    <field editable="1" name="vertices"/>
  </editable>
  <labelOnTop>
    <field name="ID" labelOnTop="0"/>
    <field name="azimuth" labelOnTop="0"/>
    <field name="blue_grad" labelOnTop="0"/>
    <field name="boundary" labelOnTop="0"/>
    <field name="dsm_grad" labelOnTop="0"/>
    <field name="green_grad" labelOnTop="0"/>
    <field name="length" labelOnTop="0"/>
    <field name="red_grad" labelOnTop="0"/>
    <field name="sinuosity" labelOnTop="0"/>
    <field name="vertices" labelOnTop="0"/>
  </labelOnTop>
  <widgets/>
  <previewExpression>ID</previewExpression>
  <mapTip></mapTip>
  <layerGeometryType>1</layerGeometryType>
</qgis>
