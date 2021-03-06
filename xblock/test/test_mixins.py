"""
Tests of the XBlock-family functionality mixins
"""
from lxml import etree
import mock
from unittest import TestCase

from xblock.core import XBlock
from xblock.fields import List, Scope, Integer, String, ScopeIds, UNIQUE_ID
from xblock.field_data import DictFieldData
from xblock.mixins import ScopedStorageMixin, HierarchyMixin, IndexInfoMixin, ViewsMixin
from xblock.runtime import Runtime


class AttrAssertionMixin(TestCase):
    """
    A mixin to add attribute assertion methods to TestCases.
    """
    def assertHasAttr(self, obj, attr):
        "Assert that `obj` has the attribute named `attr`."
        self.assertTrue(hasattr(obj, attr), "{!r} doesn't have attribute {!r}".format(obj, attr))

    def assertNotHasAttr(self, obj, attr):
        "Assert that `obj` doesn't have the attribute named `attr`."
        self.assertFalse(hasattr(obj, attr), "{!r} has attribute {!r}".format(obj, attr))


class TestScopedStorageMixin(AttrAssertionMixin, TestCase):
    "Tests of the ScopedStorageMixin."

    class ScopedStorageMixinTester(ScopedStorageMixin):
        """Toy class for ScopedStorageMixin testing"""

        field_a = Integer(scope=Scope.settings)
        field_b = Integer(scope=Scope.content)

    class ChildClass(ScopedStorageMixinTester):
        """Toy class for ModelMetaclass testing"""
        pass

    class FieldsMixin(object):
        """Toy mixin for field testing"""
        field_c = Integer(scope=Scope.settings)

    class MixinChildClass(FieldsMixin, ScopedStorageMixinTester):
        """Toy class for ScopedStorageMixin testing with mixed-in fields"""
        pass

    class MixinGrandchildClass(MixinChildClass):
        """Toy class for ScopedStorageMixin testing with inherited mixed-in fields"""
        pass

    def test_scoped_storage_mixin(self):

        # `ModelMetaclassTester` and `ChildClass` both obtain the `fields` attribute
        # from the `ModelMetaclass`. Since this is not understood by static analysis,
        # silence this error for the duration of this test.
        # pylint: disable=E1101
        self.assertIsNot(self.ScopedStorageMixinTester.fields, self.ChildClass.fields)

        self.assertHasAttr(self.ScopedStorageMixinTester, 'field_a')
        self.assertHasAttr(self.ScopedStorageMixinTester, 'field_b')

        self.assertIs(self.ScopedStorageMixinTester.field_a, self.ScopedStorageMixinTester.fields['field_a'])
        self.assertIs(self.ScopedStorageMixinTester.field_b, self.ScopedStorageMixinTester.fields['field_b'])

        self.assertHasAttr(self.ChildClass, 'field_a')
        self.assertHasAttr(self.ChildClass, 'field_b')

        self.assertIs(self.ChildClass.field_a, self.ChildClass.fields['field_a'])
        self.assertIs(self.ChildClass.field_b, self.ChildClass.fields['field_b'])

    def test_with_mixins(self):
        # Testing model metaclass with mixins

        # `MixinChildClass` and `MixinGrandchildClass` both obtain the `fields` attribute
        # from the `ScopedStorageMixin`. Since this is not understood by static analysis,
        # silence this error for the duration of this test.
        # pylint: disable=E1101

        self.assertHasAttr(self.MixinChildClass, 'field_a')
        self.assertHasAttr(self.MixinChildClass, 'field_c')
        self.assertIs(self.MixinChildClass.field_a, self.MixinChildClass.fields['field_a'])
        self.assertIs(self.FieldsMixin.field_c, self.MixinChildClass.fields['field_c'])

        self.assertHasAttr(self.MixinGrandchildClass, 'field_a')
        self.assertHasAttr(self.MixinGrandchildClass, 'field_c')
        self.assertIs(self.MixinGrandchildClass.field_a, self.MixinGrandchildClass.fields['field_a'])
        self.assertIs(self.MixinGrandchildClass.field_c, self.MixinGrandchildClass.fields['field_c'])


class TestHierarchyMixin(AttrAssertionMixin, TestCase):
    "Tests of the HierarchyMixin."

    class HasChildren(HierarchyMixin):
        """Toy class for ChildrenModelMetaclass testing"""
        has_children = True

    class WithoutChildren(HierarchyMixin):
        """Toy class for ChildrenModelMetaclass testing"""
        pass

    class InheritedChildren(HasChildren):
        """Toy class for ChildrenModelMetaclass testing"""
        pass

    def test_children_metaclass(self):
        # `HasChildren` and `WithoutChildren` both obtain the `children` attribute and
        # the `has_children` method from the `ChildrenModelMetaclass`. Since this is not
        # understood by static analysis, silence this error for the duration of this test.
        # pylint: disable=E1101

        self.assertTrue(self.HasChildren.has_children)
        self.assertFalse(self.WithoutChildren.has_children)
        self.assertTrue(self.InheritedChildren.has_children)

        self.assertHasAttr(self.HasChildren, 'children')
        self.assertNotHasAttr(self.WithoutChildren, 'children')
        self.assertHasAttr(self.InheritedChildren, 'children')

        self.assertIsInstance(self.HasChildren.children, List)
        self.assertEqual(Scope.children, self.HasChildren.children.scope)
        self.assertIsInstance(self.InheritedChildren.children, List)
        self.assertEqual(Scope.children, self.InheritedChildren.children.scope)


class TestIndexInfoMixin(AttrAssertionMixin):
    """
    Tests for Index
    """
    class IndexInfoMixinTester(IndexInfoMixin):
        """Test class for index mixin"""
        pass

    def test_index_info(self):
        self.assertHasAttr(self.IndexInfoMixinTester, 'index_dictionary')
        with_index_info = self.IndexInfoMixinTester().index_dictionary()
        self.assertFalse(with_index_info)
        self.assertTrue(isinstance(with_index_info, dict))


class TestViewsMixin(TestCase):
    """
    Tests for ViewsMixin
    """
    def test_supports_view_decorator(self):
        """
        Tests the @supports decorator for xBlock view methods
        """
        class SupportsDecoratorTester(ViewsMixin):
            """
            Test class for @supports decorator
            """
            @ViewsMixin.supports("a_functionality")
            def functionality_supported_view(self):
                """
                A view that supports a functionality
                """
                pass  # pragma: no cover

            @ViewsMixin.supports("functionality1", "functionality2")
            def multi_featured_view(self):
                """
                A view that supports multiple functionalities
                """
                pass  # pragma: no cover

            def an_unsupported_view(self):
                """
                A view that does not support any functionality
                """
                pass  # pragma: no cover

        test_xblock = SupportsDecoratorTester()

        for view_name, functionality, expected_result in (
                ("functionality_supported_view", "a_functionality", True),
                ("functionality_supported_view", "bogus_functionality", False),
                ("functionality_supported_view", None, False),

                ("an_unsupported_view", "a_functionality", False),

                ("multi_featured_view", "functionality1", True),
                ("multi_featured_view", "functionality2", True),
                ("multi_featured_view", "bogus_functionality", False),
        ):
            self.assertEquals(
                test_xblock.has_support(getattr(test_xblock, view_name), functionality),
                expected_result
            )

    def test_has_support_override(self):
        """
        Tests overriding has_support
        """
        class HasSupportOverrideTester(ViewsMixin):
            """
            Test class for overriding has_support
            """
            def has_support(self, view, functionality):
                """
                Overrides implementation of has_support
                """
                return functionality == "a_functionality"

        test_xblock = HasSupportOverrideTester()

        for view_name, functionality, expected_result in (
                ("functionality_supported_view", "a_functionality", True),
                ("functionality_supported_view", "bogus_functionality", False),
        ):
            self.assertEquals(
                test_xblock.has_support(getattr(test_xblock, view_name, None), functionality),
                expected_result
            )


class TestXmlSerializationMixin(TestCase):
    """ Tests for XmlSerialization Mixin """

    etree_node_tag = 'test_xblock'

    # pylint:disable=invalid-name
    class TestXBlock(XBlock):
        """ XBlock for XML export test """
        field = String()
        simple_default = String(default="default")
        simple_default_with_force_export = String(default="default", force_export=True)
        unique_id_default = String(default=UNIQUE_ID)
        unique_id_default_with_force_export = String(default=UNIQUE_ID, force_export=True)

    def _make_block(self):
        """ Creates a test block """
        runtime_mock = mock.Mock(spec=Runtime)
        scope_ids = ScopeIds("user_id", self.etree_node_tag, "def_id", "usage_id")
        return self.TestXBlock(runtime_mock, field_data=DictFieldData({}), scope_ids=scope_ids)

    def _assert_node_attributes(self, node, attributes):
        """ Asserts node attributes """
        node_attributes = node.keys()
        node_attributes.remove('xblock-family')

        self.assertEqual(node.get('xblock-family'), self.TestXBlock.entry_point)

        self.assertEqual(set(node_attributes), set(attributes.keys()))

        for key, value in attributes.iteritems():
            if value != UNIQUE_ID:
                self.assertEqual(node.get(key), value)
            else:
                self.assertIsNotNone(node.get(key))

    def test_add_xml_to_node(self):
        """ Tests add_xml_to_node with various field defaults and runtime parameters """
        block = self._make_block()
        node = etree.Element(self.etree_node_tag)

        # precondition check
        for field_name in block.fields.keys():
            self.assertFalse(block.fields[field_name].is_set_on(block))

        block.add_xml_to_node(node)

        self._assert_node_attributes(
            node, {'simple_default_with_force_export': 'default', 'unique_id_default_with_force_export': UNIQUE_ID}
        )

        block.field = 'Value1'
        block.simple_default = 'Value2'
        block.simple_default_with_force_export = 'Value3'
        block.unique_id_default = 'Value4'
        block.unique_id_default_with_force_export = 'Value5'

        block.add_xml_to_node(node)

        self._assert_node_attributes(
            node,
            {
                'field': 'Value1',
                'simple_default': 'Value2',
                'simple_default_with_force_export': 'Value3',
                'unique_id_default': 'Value4',
                'unique_id_default_with_force_export': 'Value5',
            }
        )
