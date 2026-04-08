import { useState } from "react";
import { Form, Input, Button, Card, Typography, App } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { useAuth } from "../hooks/useAuth";

const { Title } = Typography;

export default function LoginPage() {
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);
  const { message } = App.useApp();

  const onFinish = async (values: { email: string; password: string }) => {
    setLoading(true);
    try {
      await login(values);
    } catch {
      message.error("이메일 또는 비밀번호가 올바르지 않습니다");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        background: "#f0f2f5",
      }}
    >
      <Card style={{ width: 400 }}>
        <Title level={3} style={{ textAlign: "center" }}>
          G2B AI 로그인
        </Title>
        <Form onFinish={onFinish} size="large">
          <Form.Item
            name="email"
            rules={[{ required: true, message: "이메일을 입력하세요" }]}
          >
            <Input prefix={<UserOutlined />} placeholder="이메일" />
          </Form.Item>
          <Form.Item
            name="password"
            rules={[{ required: true, message: "비밀번호를 입력하세요" }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="비밀번호" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              로그인
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
